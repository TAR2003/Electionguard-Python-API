#!/usr/bin/env python
"""
single_election.py - Full binary (msgpack) transport client for ElectionGuard API.

All HTTP request/response bodies use msgpack (application/msgpack).
No JSON overhead. No base64 double-wrapping of outer payloads.
Inner ElectionGuard crypto objects (guardian_public_key, tally_share, etc.)
remain as base64+msgpack strings - those are handled transparently by the server.
"""

import requests
import msgpack
import random
import time
from collections import defaultdict
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =========================================================
# CONFIG
# =========================================================
BASE_URL = "http://127.0.0.1:5000"  # explicit IPv4 — avoids localhost→::1 fallback (2s delay on Windows)

NUMBER_OF_GUARDIANS = 3
QUORUM = 2
BALLOT_COUNTS = [100]

PARTY_NAMES = ["Democratic Alliance", "Progressive Coalition", "Unity Party", "Reform League"]
CANDIDATE_NAMES = ["Alice Johnson", "Bob Smith", "Carol Williams", "David Brown"]

CHUNK_SIZE = 50

MSGPACK_HEADERS = {
    "Content-Type": "application/msgpack",
    "Accept": "application/msgpack",
    # No "Connection: close" — reuse persistent connections for speed
}

# Persistent HTTP session: reuses TCP connections across all API calls (major speedup on Windows)
_http_session = requests.Session()

# =========================================================
# HELPERS
# =========================================================

import os
import json
from collections import defaultdict

# ensure the io directory exists (it should already, but just in case)
os.makedirs(os.path.join(os.path.dirname(__file__), "io"), exist_ok=True)

# counters for naming multiple calls per endpoint (not used when overwriting)
_log_counters = defaultdict(int)

def log(msg, indent=0):
    print("  " * indent + msg)


def _log_io(api_name: str, payload: object, response: object):
    """Write the request payload and response to files under io/.

    Overwrites the previous log for a given API name so only the most recent
    request/response pair is kept.  This keeps the folder trimmed and matches
    the user's request.
    """
    directory = os.path.join(os.path.dirname(__file__), "io")
    req_path = os.path.join(directory, f"{api_name}_request.json")
    resp_path = os.path.join(directory, f"{api_name}_response.json")
    try:
        with open(req_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Failed to write request log for {api_name}: {e}")
    try:
        with open(resp_path, "w", encoding="utf-8") as f:
            json.dump(response, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Failed to write response log for {api_name}: {e}")


def time_api_call(api_name, url, payload, indent=0):
    """Send msgpack request and receive msgpack response using persistent connection."""
    log(f"[API START] {api_name}", indent)
    start = time.time()

    packed = msgpack.packb(payload, use_bin_type=True, default=str)
    response = None
    try:
        response = _http_session.post(
            url,
            data=packed,
            headers=MSGPACK_HEADERS,
            verify=False,
            timeout=None,
        )
        elapsed = time.time() - start
        assert response.status_code == 200, (
            f"{api_name} failed ({response.status_code}): {response.text[:500]}"
        )
        data = msgpack.unpackb(response.content, raw=False)
        # log the request and the decoded response
        try:
            _log_io(api_name, payload, data)
        except Exception as e:
            print(f"⚠️ logging failure for {api_name}: {e}")
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass

    log(f"[API END] {api_name} ({elapsed:.3f}s)", indent)
    return data, elapsed


def chunk_list(data, size):
    for i in range(0, len(data), size):
        yield data[i:i + size]


def find_by_guardian_id(data_list, key, gid):
    """
    Find an item in a list of dicts by a key value.
    With msgpack transport, all guardian data arrives as native Python dicts.
    """
    for item in data_list:
        if isinstance(item, dict) and item.get(key) == gid:
            return item
    raise ValueError(f"Guardian {gid} not found in list (key='{key}')")


# =========================================================
# MAIN WORKFLOW
# =========================================================
def run_chunked_election(ballot_count):

    print("\n" + "=" * 120)
    print(f"STARTING ELECTION - {ballot_count} BALLOTS")
    print("=" * 120)

    # ------------------------------------------------------------------
    # STEP 1: SETUP GUARDIANS
    # ------------------------------------------------------------------
    print("\n[STEP 1] SETUP GUARDIANS")

    setup_result, _ = time_api_call(
        "setup_guardians",
        f"{BASE_URL}/setup_guardians",
        {
            "number_of_guardians": NUMBER_OF_GUARDIANS,
            "quorum": QUORUM,
            "party_names": PARTY_NAMES,
            "candidate_names": CANDIDATE_NAMES,
        },
        indent=1,
    )

    guardian_data    = setup_result["guardian_data"]
    private_keys     = setup_result["private_keys"]
    public_keys      = setup_result["public_keys"]
    polynomials      = setup_result["polynomials"]
    joint_public_key = setup_result["joint_public_key"]
    commitment_hash  = setup_result["commitment_hash"]

    # ------------------------------------------------------------------
    # STEP 2: BALLOT ENCRYPTION
    # ------------------------------------------------------------------
    print("\n[STEP 2] ENCRYPT BALLOTS")

    encrypted_ballots = []

    for i in range(ballot_count):
        log(f"Encrypting ballot {i+1}/{ballot_count}", 1)

        result, _ = time_api_call(
            "create_encrypted_ballot",
            f"{BASE_URL}/create_encrypted_ballot",
            {
                "party_names": PARTY_NAMES,
                "candidate_names": CANDIDATE_NAMES,
                "candidate_name": random.choice(CANDIDATE_NAMES),
                "ballot_id": f"ballot-{i+1}",
                "joint_public_key": joint_public_key,
                "commitment_hash": commitment_hash,
                "number_of_guardians": NUMBER_OF_GUARDIANS,
                "quorum": QUORUM,
            },
            indent=2,
        )

        encrypted_ballots.append(result["encrypted_ballot"])

    # ------------------------------------------------------------------
    # STEP 3: CHUNKING
    # ------------------------------------------------------------------
    print("\n[STEP 3] CHUNKING BALLOTS")

    chunks = list(chunk_list(encrypted_ballots, CHUNK_SIZE))
    log(f"Total chunks: {len(chunks)}", 1)

    # ==================================================================
    # PHASE 1: CREATE TALLIES (ALL CHUNKS)
    # ==================================================================
    print("\n[PHASE 1] CREATE ENCRYPTED TALLIES")

    chunk_tallies = []

    for idx, chunk in enumerate(chunks, start=1):
        print(f"\n--- TALLY CHUNK {idx}/{len(chunks)} ---")

        tally_result, _ = time_api_call(
            "create_encrypted_tally",
            f"{BASE_URL}/create_encrypted_tally",
            {
                "party_names": PARTY_NAMES,
                "candidate_names": CANDIDATE_NAMES,
                "joint_public_key": joint_public_key,
                "commitment_hash": commitment_hash,
                "encrypted_ballots": chunk,
                "number_of_guardians": NUMBER_OF_GUARDIANS,
                "quorum": QUORUM,
            },
            indent=1,
        )

        chunk_tallies.append(tally_result)

    # ==================================================================
    # PHASE 2: PARTIAL DECRYPTIONS (ALL CHUNKS)
    # ==================================================================
    print("\n[PHASE 2] PARTIAL DECRYPTIONS")

    available_ids = [str(i + 1) for i in range(QUORUM)]
    missing_ids   = [str(i + 1) for i in range(QUORUM, NUMBER_OF_GUARDIANS)]

    partial_results = []

    for idx, tally in enumerate(chunk_tallies, start=1):
        print(f"\n--- PARTIAL DECRYPT CHUNK {idx}/{len(chunk_tallies)} ---")

        ciphertext_tally  = tally["ciphertext_tally"]
        submitted_ballots = tally["submitted_ballots"]

        shares = {}

        for gid in available_ids:
            log(f"Guardian {gid} partial decrypt", 1)

            result, _ = time_api_call(
                "create_partial_decryption",
                f"{BASE_URL}/create_partial_decryption",
                {
                    "guardian_id":   gid,
                    "guardian_data": find_by_guardian_id(guardian_data, "id", gid),
                    "private_key":   find_by_guardian_id(private_keys, "guardian_id", gid),
                    "public_key":    find_by_guardian_id(public_keys, "guardian_id", gid),
                    "polynomial":    find_by_guardian_id(polynomials, "guardian_id", gid),
                    "party_names": PARTY_NAMES,
                    "candidate_names": CANDIDATE_NAMES,
                    "ciphertext_tally": ciphertext_tally,
                    "submitted_ballots": submitted_ballots,
                    "joint_public_key": joint_public_key,
                    "commitment_hash": commitment_hash,
                    "number_of_guardians": NUMBER_OF_GUARDIANS,
                    "quorum": QUORUM,
                },
                indent=2,
            )

            shares[gid] = result

        partial_results.append(shares)

    # ==================================================================
    # PHASE 3: COMPENSATED DECRYPTIONS (ALL CHUNKS)
    # ==================================================================
    print("\n[PHASE 3] COMPENSATED DECRYPTIONS")

    compensated_results = []

    for idx, tally in enumerate(chunk_tallies, start=1):
        print(f"\n--- COMPENSATED DECRYPT CHUNK {idx}/{len(chunk_tallies)} ---")

        ciphertext_tally  = tally["ciphertext_tally"]
        submitted_ballots = tally["submitted_ballots"]

        comp_tally   = []
        comp_ballots = []
        miss_ids     = []
        comp_ids     = []

        for mid in missing_ids:
            for aid in available_ids:
                log(f"{aid} compensates for {mid}", 1)

                result, _ = time_api_call(
                    "create_compensated_decryption",
                    f"{BASE_URL}/create_compensated_decryption",
                    {
                        "available_guardian_id":   aid,
                        "missing_guardian_id":     mid,
                        "available_guardian_data": find_by_guardian_id(guardian_data, "id", aid),
                        "missing_guardian_data":   find_by_guardian_id(guardian_data, "id", mid),
                        "available_private_key":   find_by_guardian_id(private_keys, "guardian_id", aid),
                        "available_public_key":    find_by_guardian_id(public_keys, "guardian_id", aid),
                        "available_polynomial":    find_by_guardian_id(polynomials, "guardian_id", aid),
                        "party_names": PARTY_NAMES,
                        "candidate_names": CANDIDATE_NAMES,
                        "ciphertext_tally": ciphertext_tally,
                        "submitted_ballots": submitted_ballots,
                        "joint_public_key": joint_public_key,
                        "commitment_hash": commitment_hash,
                        "number_of_guardians": NUMBER_OF_GUARDIANS,
                        "quorum": QUORUM,
                    },
                    indent=2,
                )

                miss_ids.append(mid)
                comp_ids.append(aid)
                comp_tally.append(result["compensated_tally_share"])
                comp_ballots.append(result["compensated_ballot_shares"])

        compensated_results.append((miss_ids, comp_ids, comp_tally, comp_ballots))

    # ==================================================================
    # PHASE 4: COMBINE & AGGREGATE
    # ==================================================================
    print("\n[PHASE 4] COMBINE & FINAL TALLY")

    final_aggregate = defaultdict(int)

    for idx, tally in enumerate(chunk_tallies, start=1):
        print(f"\n--- COMBINE CHUNK {idx}/{len(chunk_tallies)} ---")

        miss_ids, comp_ids, comp_tally, comp_ballots = compensated_results[idx - 1]
        shares = partial_results[idx - 1]

        combine_result, _ = time_api_call(
            "combine_decryption_shares",
            f"{BASE_URL}/combine_decryption_shares",
            {
                "party_names": PARTY_NAMES,
                "candidate_names": CANDIDATE_NAMES,
                "joint_public_key": joint_public_key,
                "commitment_hash": commitment_hash,
                "ciphertext_tally": tally["ciphertext_tally"],
                "submitted_ballots": tally["submitted_ballots"],
                "guardian_data": guardian_data,
                "available_guardian_ids":         available_ids,
                "available_guardian_public_keys": [shares[g]["guardian_public_key"] for g in available_ids],
                "available_tally_shares":         [shares[g]["tally_share"] for g in available_ids],
                "available_ballot_shares":        [shares[g]["ballot_shares"] for g in available_ids],
                "missing_guardian_ids":           miss_ids,
                "compensating_guardian_ids":      comp_ids,
                "compensated_tally_shares":       comp_tally,
                "compensated_ballot_shares":      comp_ballots,
                "quorum": QUORUM,
                "number_of_guardians": NUMBER_OF_GUARDIANS,
            },
            indent=1,
        )

        # results is a plain dict from msgpack response - no decoding needed
        candidates = combine_result["results"]["results"]["candidates"]
        for cid, info in candidates.items():
            final_aggregate[cid] += int(float(info.get("votes", 0)))

    # ------------------------------------------------------------------
    # FINAL RESULT
    # ------------------------------------------------------------------
    print("\n" + "=" * 120)
    print("FINAL AGGREGATED RESULT")
    print("=" * 120)

    total = sum(final_aggregate.values())
    for cid, votes in final_aggregate.items():
        pct = (votes / total * 100) if total else 0
        print(f"{cid}: {votes} votes ({pct:.2f}%)")

    print("=" * 120)


# =========================================================
# ENTRY POINT
# =========================================================
if __name__ == "__main__":
    try:
        for ballots in BALLOT_COUNTS:
            run_chunked_election(ballots)
    finally:
        _http_session.close()
