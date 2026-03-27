#!/usr/bin/env python
"""
AmarVote ElectionGuard API Simulation
======================================
End-to-end election simulation that calls the Flask microservice HTTP API.
Demonstrates all API endpoints in the correct order:
  1. /setup_guardians          -- Guardian key ceremony
  2. /create_encrypted_ballot  -- Per-voter ballot encryption
  3. /benaloh_challenge         -- Cryptographic ballot audit (one ballot)
  4. /create_encrypted_tally   -- Homomorphic tally of all cast ballots
  5. /create_partial_decryption -- Per-guardian decryption shares
  6. /combine_decryption_shares -- Final tallying and result revelation

Usage:
    python sample_election_simulation.py [--url http://host:port]

Requirements:
    pip install requests msgpack
"""

import argparse
import sys
import time
import uuid
from typing import Any, Dict, List, Tuple

import msgpack
import requests

# ============================================================================
# CONFIGURATION -- tweak these to match your election scenario
# ============================================================================

DEFAULT_BASE_URL = "http://localhost:5000"

PARTY_NAMES: List[str] = [
    "Party A",
    "Party B",
]

CANDIDATE_NAMES: List[str] = [
    "Alice Johnson",
    "Donald Trump",
]

NUMBER_OF_GUARDIANS: int = 3
QUORUM: int = 2
MAX_CHOICES: int = 1   # number of candidates a voter may select per contest

# Each entry: (voter_label, [candidates_to_vote_for])
VOTER_BALLOTS: List[Tuple[str, List[str]]] = [
    ("voter-1", ["Alice Johnson"]),
    ("voter-2", ["Donald Trump"]),
    ("voter-3", ["Alice Johnson"]),
    ("voter-4", ["Donald Trump"]),
    ("voter-5", ["Alice Johnson"]),
]

# ============================================================================
# HTTP HELPER
# ============================================================================

def _bytes_to_str(obj: Any) -> Any:
    """Recursively convert bytes to str (for legacy msgpack raw=True payloads)."""
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    if isinstance(obj, dict):
        return {_bytes_to_str(k): _bytes_to_str(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_bytes_to_str(v) for v in obj]
    return obj


def _decode_response(resp: requests.Response) -> Dict[str, Any]:
    """
    Decode a microservice response.

    The API always returns msgpack-packed binary.  Fall back to JSON only as a
    last resort (e.g. plain-text error pages from a reverse proxy).
    """
    try:
        return msgpack.unpackb(resp.content, raw=False)
    except Exception:
        try:
            # Legacy format: raw=True packed without use_bin_type
            raw = msgpack.unpackb(resp.content, raw=True)
            return _bytes_to_str(raw)
        except Exception:
            return resp.json()


def post(base_url: str, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """POST a JSON payload to *endpoint* and return the decoded response dict."""
    url = f"{base_url}{endpoint}"
    try:
        resp = requests.post(url, json=data, timeout=300)
    except requests.exceptions.ConnectionError as exc:
        print(f"\nERROR: Cannot reach {url}")
        print(f"   Make sure the ElectionGuard microservice is running on {base_url}")
        print(f"   Details: {exc}")
        sys.exit(1)

    result = _decode_response(resp)
    if resp.status_code != 200:
        message = (
            result.get("message", resp.text[:300])
            if isinstance(result, dict)
            else resp.text[:300]
        )
        raise RuntimeError(f"{endpoint} returned HTTP {resp.status_code}: {message}")
    return result


def _section(title: str) -> None:
    line = "=" * 72
    print(f"\n{line}")
    print(f"  {title}")
    print(line)


# ============================================================================
# STEP 1 -- Guardian Key Ceremony
# ============================================================================

def step_setup_guardians(base_url: str) -> Dict[str, Any]:
    """Call /setup_guardians to initialise the key ceremony and joint election key."""
    _section("STEP 1 -- Guardian Key Ceremony")

    result = post(base_url, "/setup_guardians", {
        "number_of_guardians": NUMBER_OF_GUARDIANS,
        "quorum": QUORUM,
        "party_names": PARTY_NAMES,
        "candidate_names": CANDIDATE_NAMES,
    })

    if result.get("status") != "success":
        raise RuntimeError(f"Guardian setup failed: {result}")

    print(f"  {NUMBER_OF_GUARDIANS} guardians created, quorum = {QUORUM}")
    print(f"  Joint public key (first 40 chars): {str(result['joint_public_key'])[:40]}...")
    print(f"  Commitment hash  (first 40 chars): {str(result['commitment_hash'])[:40]}...")
    return result


# ============================================================================
# STEP 2 -- Ballot Encryption
# ============================================================================

def step_encrypt_ballots(
    base_url: str,
    setup: Dict[str, Any],
) -> List[str]:
    """
    Encrypt every ballot in VOTER_BALLOTS via /create_encrypted_ballot.

    Returns the list of *encrypted_ballot_with_nonce* strings required for
    the tally and benaloh challenge steps.
    """
    _section("STEP 2 -- Ballot Encryption")

    encrypted_with_nonce: List[str] = []

    for voter_label, candidates in VOTER_BALLOTS:
        ballot_id = f"ballot-{voter_label}-{uuid.uuid4().hex[:8]}"
        result = post(base_url, "/create_encrypted_ballot", {
            "party_names": PARTY_NAMES,
            "candidate_names": CANDIDATE_NAMES,
            "candidate_names_to_vote": candidates,   # List[str] -- multi-choice ready
            "ballot_id": ballot_id,
            "joint_public_key": setup["joint_public_key"],
            "commitment_hash": setup["commitment_hash"],
            "number_of_guardians": NUMBER_OF_GUARDIANS,
            "quorum": QUORUM,
            "max_choices": MAX_CHOICES,
            "ballot_status": "CAST",
        })

        if result.get("status") != "success":
            raise RuntimeError(f"Ballot encryption failed for {voter_label}: {result}")

        nonce_token = result["encrypted_ballot_with_nonce"]
        ballot_hash = result.get("ballot_hash", "N/A")
        encrypted_with_nonce.append(nonce_token)
        print(f"  Encrypted {voter_label} -> {candidates}  |  hash: {str(ballot_hash)[:24]}...")

    print(f"\n  Total encrypted: {len(encrypted_with_nonce)} ballots")
    return encrypted_with_nonce


# ============================================================================
# STEP 3 -- Benaloh Challenge (cryptographic audit of one ballot)
# ============================================================================

def step_benaloh_challenge(
    base_url: str,
    setup: Dict[str, Any],
    encrypted_with_nonce: List[str],
    voter_index: int = 0,
) -> None:
    """
    Perform a Benaloh challenge on one encrypted ballot via /benaloh_challenge.

    The challenge decrypts the ballot nonces and verifies that the encrypted
    choices match what the voter actually selected.
    """
    _section("STEP 3 -- Benaloh Challenge (ballot audit)")

    voter_label, candidates_to_verify = VOTER_BALLOTS[voter_index]
    print(f"  Challenging ballot for {voter_label} -> claimed vote: {candidates_to_verify}")

    result = post(base_url, "/benaloh_challenge", {
        "encrypted_ballot_with_nonce": encrypted_with_nonce[voter_index],
        "party_names": PARTY_NAMES,
        "candidate_names": CANDIDATE_NAMES,
        "candidate_names_to_verify": candidates_to_verify,   # List[str]
        "joint_public_key": setup["joint_public_key"],
        "commitment_hash": setup["commitment_hash"],
        "number_of_guardians": NUMBER_OF_GUARDIANS,
        "quorum": QUORUM,
    })

    if result.get("status") != "success":
        raise RuntimeError(f"Benaloh challenge failed: {result}")

    match = result.get("match", False)
    verified = result.get("verified_candidates", result.get("verified_candidate", "?"))
    status_icon = "OK" if match else "MISMATCH"
    print(f"  [{status_icon}] Challenge result: match = {match}")
    print(f"  Verified candidates: {verified}")
    if not match:
        print(f"  Message: {result.get('message', '')}")
        print("  WARNING: Ballot integrity issue -- in a real election this ballot would be spoiled.")


# ============================================================================
# STEP 4 -- Encrypted Tally
# ============================================================================

def step_tally(
    base_url: str,
    setup: Dict[str, Any],
    encrypted_with_nonce: List[str],
) -> Dict[str, Any]:
    """Homomorphically tally all cast ballots via /create_encrypted_tally."""
    _section("STEP 4 -- Encrypted Tally")

    result = post(base_url, "/create_encrypted_tally", {
        "party_names": PARTY_NAMES,
        "candidate_names": CANDIDATE_NAMES,
        "joint_public_key": setup["joint_public_key"],
        "commitment_hash": setup["commitment_hash"],
        "encrypted_ballots": encrypted_with_nonce,   # list of binary-transport strings
        "number_of_guardians": NUMBER_OF_GUARDIANS,
        "quorum": QUORUM,
        "max_choices": MAX_CHOICES,
    })

    if result.get("status") != "success":
        raise RuntimeError(f"Tally failed: {result}")

    n_submitted = len(result.get("submitted_ballots", []))
    print(f"  Encrypted tally created  |  {n_submitted} submitted ballots recorded")
    return result


# ============================================================================
# STEP 5 -- Partial Decryption (one call per guardian)
# ============================================================================

def step_partial_decryptions(
    base_url: str,
    setup: Dict[str, Any],
    tally: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Ask each guardian to compute its partial decryption share via
    /create_partial_decryption.
    """
    _section("STEP 5 -- Partial Decryption (per guardian)")

    guardian_data_list: List[Dict] = setup["guardian_data"]
    private_keys: List[Dict] = setup["private_keys"]
    public_keys: List[Dict] = setup["public_keys"]

    shares: List[Dict[str, Any]] = []

    for i in range(NUMBER_OF_GUARDIANS):
        guardian_id = str(i + 1)   # guardian IDs are "1", "2", "3", ...

        result = post(base_url, "/create_partial_decryption", {
            "guardian_id": guardian_id,
            # Single guardian data (service validates guardian_data['id'] == guardian_id)
            "guardian_data": guardian_data_list[i],
            "private_key": private_keys[i],    # {"guardian_id": ..., "private_key": "..."}
            "public_key": public_keys[i],      # {"guardian_id": ..., "public_key": "..."}
            "party_names": PARTY_NAMES,
            "candidate_names": CANDIDATE_NAMES,
            # Pass tally data as-is (dicts/lists from previous response)
            "ciphertext_tally": tally["ciphertext_tally"],
            "submitted_ballots": tally["submitted_ballots"],
            "joint_public_key": setup["joint_public_key"],
            "commitment_hash": setup["commitment_hash"],
            "number_of_guardians": NUMBER_OF_GUARDIANS,
            "quorum": QUORUM,
            "max_choices": MAX_CHOICES,
        })

        if result.get("status") != "success":
            raise RuntimeError(
                f"Partial decryption failed for guardian {guardian_id}: {result}"
            )

        shares.append(result)
        n_ballot_shares = len(result.get("ballot_shares") or {})
        print(f"  Guardian {guardian_id} -- tally share computed  ({n_ballot_shares} ballot shares)")

    return shares


# ============================================================================
# STEP 6 -- Combine Decryption Shares -> Final Results
# ============================================================================

def step_combine_shares(
    base_url: str,
    setup: Dict[str, Any],
    tally: Dict[str, Any],
    shares: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Combine all guardian partial-decryption shares via /combine_decryption_shares
    to reveal the final election results.
    """
    _section("STEP 6 -- Combine Decryption Shares")

    guardian_ids = [str(i + 1) for i in range(NUMBER_OF_GUARDIANS)]

    result = post(base_url, "/combine_decryption_shares", {
        "party_names": PARTY_NAMES,
        "candidate_names": CANDIDATE_NAMES,
        "joint_public_key": setup["joint_public_key"],
        "commitment_hash": setup["commitment_hash"],
        # Tally and submitted ballots (pass through from step 4)
        "ciphertext_tally": tally["ciphertext_tally"],
        "submitted_ballots": tally["submitted_ballots"],
        # All guardian metadata (needed for compensated decryption bookkeeping)
        "guardian_data": setup["guardian_data"],
        # Available guardian shares (all guardians present in this demo)
        "available_guardian_ids": guardian_ids,
        "available_guardian_public_keys": [s["guardian_public_key"] for s in shares],
        "available_tally_shares": [s["tally_share"] for s in shares],
        # ballot_shares is {ballot_id -> binary-transport-string}; pass dict as-is
        "available_ballot_shares": [s["ballot_shares"] for s in shares],
        # No missing guardians in this demo
        "missing_guardian_ids": [],
        "compensating_guardian_ids": [],
        "compensated_tally_shares": [],
        "compensated_ballot_shares": [],
        "quorum": QUORUM,
        "number_of_guardians": NUMBER_OF_GUARDIANS,
        "max_choices": MAX_CHOICES,
    })

    if result.get("status") != "success":
        raise RuntimeError(f"Combine decryption shares failed: {result}")

    print("  All decryption shares combined -- results decrypted successfully")
    return result.get("results", result)


# ============================================================================
# DISPLAY RESULTS
# ============================================================================

def display_results(results: Dict[str, Any]) -> None:
    _section("ELECTION RESULTS")

    if not results:
        print("  ERROR: No results to display")
        return

    candidate_results: Dict[str, Any] = (
        results.get("results", {}).get("candidates", {})
    )

    if candidate_results:
        print("\n  VOTE COUNTS:")
        sorted_candidates = sorted(
            candidate_results.items(),
            key=lambda kv: int(kv[1].get("votes", 0)),
            reverse=True,
        )
        for candidate, data in sorted_candidates:
            votes = int(data.get("votes", 0))
            try:
                pct = float(data.get("percentage", 0))
            except (TypeError, ValueError):
                pct = 0.0
            filled = int(pct / 5)
            bar = "#" * filled + "-" * (20 - filled)
            print(f"    {candidate:<28} [{bar}] {votes:3d} votes  ({pct:.1f}%)")
    else:
        print("  WARNING: No candidate vote counts found in results")

    r = results.get("results", {})
    total   = r.get("total_ballots_cast", "?")
    valid   = r.get("total_valid_ballots", "?")
    spoiled = r.get("total_spoiled_ballots", "?")
    print(f"\n  SUMMARY:  Total cast = {total}  |  Valid = {valid}  |  Spoiled = {spoiled}")

    # Validate against expected vote counts
    expected: Dict[str, int] = {}
    for _, candidates in VOTER_BALLOTS:
        for c in candidates:
            expected[c] = expected.get(c, 0) + 1

    print("\n  VALIDATION:")
    all_ok = True
    for candidate, exp in expected.items():
        actual = int(candidate_results.get(candidate, {}).get("votes", 0))
        ok = actual == exp
        status = "PASS" if ok else "FAIL"
        print(f"    [{status}] {candidate}: expected = {exp},  actual = {actual}")
        if not ok:
            all_ok = False

    if all_ok:
        print("\n  All vote counts match expected values!")
    else:
        print("\n  WARNING: Some vote counts differ from expected values.")

    # Ballot verification section
    verification = results.get("verification", {})
    ballot_records = verification.get("ballots", [])
    if ballot_records:
        print(f"\n  BALLOT VERIFICATION ({len(ballot_records)} ballots):")
        for b in ballot_records:
            status = b.get("status", "?")
            print(f"    [{status.upper():<7}] {b.get('ballot_id', '?')[:52]}")

    # Guardian section
    guardians = verification.get("guardians", [])
    if guardians:
        print(f"\n  GUARDIANS ({len(guardians)}):")
        for g in guardians:
            print(f"    Guardian {g.get('id', '?')} "
                  f"(seq={g.get('sequence_order', '?')})  "
                  f"status: {g.get('status', 'available')}")


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="AmarVote ElectionGuard end-to-end API simulation"
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_BASE_URL,
        help=f"Base URL of the ElectionGuard microservice (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--no-challenge",
        action="store_true",
        help="Skip the Benaloh challenge step",
    )
    args = parser.parse_args()
    base_url = args.url.rstrip("/")

    print("\n" + "=" * 72)
    print("  AmarVote -- ElectionGuard API End-to-End Simulation")
    print("=" * 72)
    print(f"\n  Server       : {base_url}")
    print(f"  Parties      : {PARTY_NAMES}")
    print(f"  Candidates   : {CANDIDATE_NAMES}")
    print(f"  Guardians    : {NUMBER_OF_GUARDIANS}  (quorum = {QUORUM})")
    print(f"  Voters       : {len(VOTER_BALLOTS)}")
    print(f"  Max choices  : {MAX_CHOICES}")

    start_time = time.time()

    # --- Run all steps ---
    setup = step_setup_guardians(base_url)
    encrypted_with_nonce = step_encrypt_ballots(base_url, setup)

    if not args.no_challenge:
        step_benaloh_challenge(base_url, setup, encrypted_with_nonce, voter_index=0)

    tally = step_tally(base_url, setup, encrypted_with_nonce)
    shares = step_partial_decryptions(base_url, setup, tally)
    results = step_combine_shares(base_url, setup, tally, shares)

    display_results(results)

    elapsed = time.time() - start_time
    _section(f"SIMULATION COMPLETE  ({elapsed:.2f}s)")
    print(f"  {len(VOTER_BALLOTS)} voters, {NUMBER_OF_GUARDIANS} guardians -- "
          f"full ElectionGuard pipeline ran successfully!\n")


if __name__ == "__main__":
    main()
