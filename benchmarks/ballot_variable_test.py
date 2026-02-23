#!/usr/bin/env python
"""
ballot_variable_test.py - ElectionGuard scalability test.
Uses msgpack transport (application/msgpack) for max performance.
"""

import requests
import msgpack
import json
import random
import time
from typing import Dict, List, Tuple
from collections import defaultdict
from statistics import mean, stdev

import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API Base URL
BASE_URL = "http://127.0.0.1:5000"  # explicit IPv4 — avoids localhost→::1 fallback (2s delay on Windows)

# Test Configuration - HARDCODED VALUES
NUMBER_OF_GUARDIANS = 5
QUORUM = 3
BALLOT_COUNTS = [32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072]  # Array of ballot counts to test
PARTY_NAMES = ["Democratic Alliance", "Progressive Coalition", "Unity Party", "Reform League"]
CANDIDATE_NAMES = ["Alice Johnson", "Bob Smith", "Carol Williams", "David Brown"]

# Tally chunk size — avoids server timeouts for large ballot counts
CHUNK_SIZE = 1000

# Msgpack transport headers
MSGPACK_HEADERS = {
    "Content-Type": "application/msgpack",
    "Accept": "application/msgpack",
}

# Persistent HTTP session — reuses TCP connections across all API calls (major speedup on Windows)
_http_session = requests.Session()

# Timing tracker
timing_data = defaultdict(list)
# Size tracker (request and response sizes)
size_data = defaultdict(lambda: {'request_sizes': [], 'response_sizes': []})
# Store results for each ballot count
all_results = {}


def format_size(size_bytes: int) -> str:
    """Format size in bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f}TB"


def time_api_call(api_name: str, url: str, payload: dict) -> Tuple[dict, float]:
    """Send msgpack request, receive msgpack response, and record timing/sizes."""
    packed = msgpack.packb(payload, use_bin_type=True, default=str)
    request_size = len(packed)

    start_time = time.time()
    response = _http_session.post(
        url, data=packed, headers=MSGPACK_HEADERS, verify=False, timeout=None
    )
    elapsed_time = time.time() - start_time

    response_size = len(response.content)
    timing_data[api_name].append(elapsed_time)
    size_data[api_name]['request_sizes'].append(request_size)
    size_data[api_name]['response_sizes'].append(response_size)

    assert response.status_code == 200, f"{api_name} failed ({response.status_code}): {response.text[:500]}"
    data = msgpack.unpackb(response.content, raw=False)
    return data, elapsed_time


def chunk_list(data, size):
    """Split a list into chunks of the given size."""
    for i in range(0, len(data), size):
        yield data[i:i + size]


def find_guardian_data(guardian_id: str, guardian_data_list: list,
                       private_keys_list: list, public_keys_list: list,
                       polynomials_list: list):
    """
    Find data for a specific guardian from the lists.
    With msgpack transport, all guardian data arrives as native Python dicts —
    no json.loads() needed.
    """
    def _find(lst, key):
        for item in lst:
            if isinstance(item, dict) and item.get(key) == guardian_id:
                return item
        raise ValueError(f"Guardian {guardian_id} not found (key='{key}')")

    gd   = _find(guardian_data_list, 'id')
    pk   = _find(private_keys_list,  'guardian_id')
    pubk = _find(public_keys_list,   'guardian_id')
    poly = _find(polynomials_list,   'guardian_id')

    if not all([gd, pk, pubk, poly]):
        raise ValueError(f"Missing data for guardian {guardian_id}")

    return gd, pk, pubk, poly


def print_timing_summary():
    """Print a formatted summary of all API timing data."""
    print("\n" + "=" * 150)
    print("API PERFORMANCE SUMMARY")
    print("=" * 150)
    print(f"{'API Endpoint':<40} {'Calls':<8} {'Avg Time':<12} {'Min Time':<12} {'Max Time':<12} {'Std Dev':<12} {'Avg Req':<12} {'Avg Resp':<12}")
    print("-" * 150)
    
    total_time = 0
    total_calls = 0
    
    for api_name in sorted(timing_data.keys()):
        times = timing_data[api_name]
        num_calls = len(times)
        avg_time = mean(times)
        min_time = min(times)
        max_time = max(times)
        std_dev = stdev(times) if len(times) > 1 else 0.0
        
        # Calculate average sizes
        req_sizes = size_data[api_name]['request_sizes']
        resp_sizes = size_data[api_name]['response_sizes']
        avg_req_size = format_size(mean(req_sizes)) if req_sizes else 'N/A'
        avg_resp_size = format_size(mean(resp_sizes)) if resp_sizes else 'N/A'
        
        total_time += sum(times)
        total_calls += num_calls
        
        print(f"{api_name:<40} {num_calls:<8} {avg_time:<12.4f}s {min_time:<12.4f}s {max_time:<12.4f}s {std_dev:<12.4f}s {avg_req_size:<12} {avg_resp_size:<12}")
    
    print("-" * 150)
    print(f"{'TOTAL':<40} {total_calls:<8} {total_time:<12.4f}s")
    print("=" * 150)


def get_timing_stats():
    """Get timing statistics as a dictionary."""
    stats = {}
    total_time = 0
    
    for api_name in sorted(timing_data.keys()):
        times = timing_data[api_name]
        num_calls = len(times)
        avg_time = mean(times)
        min_time = min(times)
        max_time = max(times)
        std_dev = stdev(times) if len(times) > 1 else 0.0
        
        # Calculate average sizes
        req_sizes = size_data[api_name]['request_sizes']
        resp_sizes = size_data[api_name]['response_sizes']
        avg_req_size = mean(req_sizes) if req_sizes else 0
        avg_resp_size = mean(resp_sizes) if resp_sizes else 0
        
        stats[api_name] = {
            'calls': num_calls,
            'avg_time': avg_time,
            'min_time': min_time,
            'max_time': max_time,
            'std_dev': std_dev,
            'total_time': sum(times),
            'avg_req_size': avg_req_size,
            'avg_resp_size': avg_resp_size
        }
        
        total_time += sum(times)
    
    stats['TOTAL'] = {
        'total_time': total_time,
        'total_calls': sum(s['calls'] for s in stats.values() if isinstance(s, dict) and 'calls' in s)
    }
    
    return stats


def export_results_to_file(ballot_count, stats, previous_ballot_count=None, previous_stats=None):
    """Export results to a text file with comparison to previous run if available."""
    filename = "election_performance_results.txt"
    
    with open(filename, 'a', encoding='utf-8') as f:
        f.write("\n" + "=" * 200 + "\n")
        f.write(f"ELECTION WORKFLOW PERFORMANCE TEST - {ballot_count} BALLOTS\n")
        f.write("=" * 200 + "\n")
        f.write(f"Configuration:\n")
        f.write(f"  - Guardians: {NUMBER_OF_GUARDIANS}\n")
        f.write(f"  - Quorum: {QUORUM}\n")
        f.write(f"  - Ballots: {ballot_count}\n")
        f.write(f"  - Parties: {len(PARTY_NAMES)}\n")
        f.write(f"  - Candidates: {len(CANDIDATE_NAMES)}\n")
        
        if previous_ballot_count:
            ratio = ballot_count / previous_ballot_count
            f.write(f"  - Comparative to previous: {ratio:.4f}x ({previous_ballot_count} ballots)\n")
        
        f.write("\n" + "-" * 200 + "\n")
        f.write("API PERFORMANCE SUMMARY\n")
        f.write("-" * 200 + "\n")
        f.write(f"{'API Endpoint':<40} {'Calls':<8} {'Avg Time':<12} {'Min Time':<12} {'Max Time':<12} {'Std Dev':<12} {'Avg Req':<12} {'Avg Resp':<12}")
        
        if previous_stats:
            f.write(f" {'Time Ratio':<12} {'Req Ratio':<12} {'Resp Ratio':<12}")
        
        f.write("\n" + "-" * 200 + "\n")
        
        for api_name in sorted([k for k in stats.keys() if k != 'TOTAL']):
            s = stats[api_name]
            avg_req_str = format_size(s['avg_req_size'])
            avg_resp_str = format_size(s['avg_resp_size'])
            f.write(f"{api_name:<40} {s['calls']:<8} {s['avg_time']:<12.4f}s {s['min_time']:<12.4f}s {s['max_time']:<12.4f}s {s['std_dev']:<12.4f}s {avg_req_str:<12} {avg_resp_str:<12}")
            
            if previous_stats and api_name in previous_stats:
                prev_avg_time = previous_stats[api_name]['avg_time']
                time_ratio = s['avg_time'] / prev_avg_time if prev_avg_time > 0 else 0
                
                prev_avg_req = previous_stats[api_name]['avg_req_size']
                req_ratio = s['avg_req_size'] / prev_avg_req if prev_avg_req > 0 else 0
                
                prev_avg_resp = previous_stats[api_name]['avg_resp_size']
                resp_ratio = s['avg_resp_size'] / prev_avg_resp if prev_avg_resp > 0 else 0
                
                f.write(f" {time_ratio:<12.4f} {req_ratio:<12.4f} {resp_ratio:<12.4f}")
            elif previous_stats:
                f.write(f" {'N/A':<12} {'N/A':<12} {'N/A':<12}")
            
            f.write("\n")
        
        f.write("-" * 200 + "\n")
        f.write(f"{'TOTAL':<40} {stats['TOTAL']['total_calls']:<8} {stats['TOTAL']['total_time']:<12.4f}s")
        
        if previous_stats and 'TOTAL' in previous_stats:
            prev_total = previous_stats['TOTAL']['total_time']
            ratio = stats['TOTAL']['total_time'] / prev_total if prev_total > 0 else 0
            f.write(f"{'':<62} {ratio:<12.4f}")
        
        f.write("\n")
        f.write("=" * 200 + "\n\n")
    
    print(f"\n📄 Results exported to {filename}")


def run_election_workflow_with_timing(number_of_ballots):
    """Run the complete election workflow and measure all API response times.

    Large ballot counts are split into CHUNK_SIZE chunks so each tally call
    stays well under timeout limits. Results are aggregated across chunks.
    """

    print("=" * 100)
    print("ELECTION WORKFLOW PERFORMANCE TEST")
    print("=" * 100)
    print(f"Configuration:")
    print(f"  - Guardians:  {NUMBER_OF_GUARDIANS}")
    print(f"  - Quorum:     {QUORUM}")
    print(f"  - Ballots:    {number_of_ballots}")
    print(f"  - Chunk size: {CHUNK_SIZE}")
    print(f"  - Parties:    {len(PARTY_NAMES)}")
    print(f"  - Candidates: {len(CANDIDATE_NAMES)}")
    print("=" * 100)

    # ------------------------------------------------------------------
    # STEP 1: Setup Guardians
    # ------------------------------------------------------------------
    print("\n🔹 STEP 1: Setting up guardians...")
    setup_result, setup_time = time_api_call(
        "setup_guardians",
        f"{BASE_URL}/setup_guardians",
        {
            "number_of_guardians": NUMBER_OF_GUARDIANS,
            "quorum": QUORUM,
            "party_names": PARTY_NAMES,
            "candidate_names": CANDIDATE_NAMES,
        },
    )
    print(f"✅ Guardian setup completed in {setup_time:.4f}s")

    # Extract setup data — all values arrive as native Python types via msgpack
    joint_public_key    = setup_result['joint_public_key']
    commitment_hash     = setup_result['commitment_hash']
    guardian_data       = setup_result['guardian_data']   # list of dicts
    private_keys        = setup_result['private_keys']    # list of dicts
    public_keys         = setup_result['public_keys']     # list of dicts
    polynomials         = setup_result['polynomials']     # list of dicts
    number_of_guardians = setup_result['number_of_guardians']
    quorum              = setup_result['quorum']

    # ------------------------------------------------------------------
    # STEP 2: Encrypt ballots
    # ------------------------------------------------------------------
    print(f"\n🔹 STEP 2: Creating {number_of_ballots} encrypted ballots...")
    all_encrypted_ballots = []

    for i in range(number_of_ballots):
        ballot_result, _ = time_api_call(
            "create_encrypted_ballot",
            f"{BASE_URL}/create_encrypted_ballot",
            {
                "party_names": PARTY_NAMES,
                "candidate_names": CANDIDATE_NAMES,
                "candidate_name": random.choice(CANDIDATE_NAMES),
                "ballot_id": f"ballot-{i + 1}",
                "joint_public_key": joint_public_key,
                "commitment_hash": commitment_hash,
                "number_of_guardians": number_of_guardians,
                "quorum": quorum,
            },
        )
        all_encrypted_ballots.append(ballot_result['encrypted_ballot'])

        if (i + 1) % 100 == 0:
            print(f"  ✓ Encrypted {i + 1}/{number_of_ballots} ballots...")

    print(f"✅ All {number_of_ballots} ballots encrypted")

    # ------------------------------------------------------------------
    # STEP 3: Split into chunks
    # ------------------------------------------------------------------
    chunks = list(chunk_list(all_encrypted_ballots, CHUNK_SIZE))
    print(f"\n🔹 STEP 3: Processing {len(chunks)} chunk(s) of up to {CHUNK_SIZE} ballots each...")

    # Guardian selection: first QUORUM guardians available, rest missing
    available_guardian_ids = [str(i + 1) for i in range(QUORUM)]
    missing_guardian_ids   = [str(i + 1) for i in range(QUORUM, NUMBER_OF_GUARDIANS)]
    print(f"  ✓ Available guardians: {', '.join(available_guardian_ids)}")
    print(f"  ✓ Missing guardians:   {', '.join(missing_guardian_ids)}")

    # Accumulate vote totals across all chunks
    final_vote_totals: Dict[str, int] = defaultdict(int)
    last_results = None  # keep the last chunk's result for metadata

    for chunk_idx, chunk in enumerate(chunks, start=1):
        chunk_label = f"chunk {chunk_idx}/{len(chunks)} ({len(chunk)} ballots)"
        print(f"\n{'─' * 60}")
        print(f"[CHUNK {chunk_idx}/{len(chunks)}] Processing {len(chunk)} ballots...")
        print(f"{'─' * 60}")

        # ----------------------------------------------------------
        # STEP 3a: Tally this chunk
        # ----------------------------------------------------------
        print(f"  🔸 Tallying {chunk_label}...")
        tally_result, tally_time = time_api_call(
            "create_encrypted_tally",
            f"{BASE_URL}/create_encrypted_tally",
            {
                "party_names": PARTY_NAMES,
                "candidate_names": CANDIDATE_NAMES,
                "joint_public_key": joint_public_key,
                "commitment_hash": commitment_hash,
                "encrypted_ballots": chunk,
                "number_of_guardians": number_of_guardians,
                "quorum": quorum,
            },
        )
        print(f"  ✅ Tally done in {tally_time:.4f}s")

        ciphertext_tally  = tally_result['ciphertext_tally']
        submitted_ballots = tally_result['submitted_ballots']

        # ----------------------------------------------------------
        # STEP 3b: Partial decryption (available guardians)
        # ----------------------------------------------------------
        print(f"  🔸 Partial decryptions ({len(available_guardian_ids)} guardians)...")
        chunk_shares: Dict[str, dict] = {}

        for gid in available_guardian_ids:
            gd, pk, pubk, poly = find_guardian_data(
                gid, guardian_data, private_keys, public_keys, polynomials
            )
            partial_result, partial_time = time_api_call(
                "create_partial_decryption",
                f"{BASE_URL}/create_partial_decryption",
                {
                    "guardian_id":     gid,
                    "guardian_data":   gd,
                    "private_key":     pk,
                    "public_key":      pubk,
                    "polynomial":      poly,
                    "party_names":     PARTY_NAMES,
                    "candidate_names": CANDIDATE_NAMES,
                    "ciphertext_tally":   ciphertext_tally,
                    "submitted_ballots":  submitted_ballots,
                    "joint_public_key":   joint_public_key,
                    "commitment_hash":    commitment_hash,
                    "number_of_guardians": number_of_guardians,
                    "quorum":             quorum,
                },
            )
            chunk_shares[gid] = partial_result
            print(f"    ✓ Guardian {gid} partial decrypt in {partial_time:.4f}s")

        # ----------------------------------------------------------
        # STEP 3c: Compensated decryption (missing guardians)
        # ----------------------------------------------------------
        print(f"  🔸 Compensated decryptions ({len(missing_guardian_ids)} missing)...")
        miss_ids_flat, comp_ids_flat = [], []
        comp_tally_shares, comp_ballot_shares = [], []

        for mid in missing_guardian_ids:
            mgd, _, _, _ = find_guardian_data(
                mid, guardian_data, private_keys, public_keys, polynomials
            )
            for aid in available_guardian_ids:
                agd, apk, apubk, apoly = find_guardian_data(
                    aid, guardian_data, private_keys, public_keys, polynomials
                )
                comp_result, comp_time = time_api_call(
                    "create_compensated_decryption",
                    f"{BASE_URL}/create_compensated_decryption",
                    {
                        "available_guardian_id":   aid,
                        "missing_guardian_id":     mid,
                        "available_guardian_data": agd,
                        "missing_guardian_data":   mgd,
                        "available_private_key":   apk,
                        "available_public_key":    apubk,
                        "available_polynomial":    apoly,
                        "party_names":     PARTY_NAMES,
                        "candidate_names": CANDIDATE_NAMES,
                        "ciphertext_tally":    ciphertext_tally,
                        "submitted_ballots":   submitted_ballots,
                        "joint_public_key":    joint_public_key,
                        "commitment_hash":     commitment_hash,
                        "number_of_guardians": number_of_guardians,
                        "quorum":              quorum,
                    },
                )
                miss_ids_flat.append(mid)
                comp_ids_flat.append(aid)
                comp_tally_shares.append(comp_result['compensated_tally_share'])
                comp_ballot_shares.append(comp_result['compensated_ballot_shares'])
                print(f"    ✓ Guardian {aid} compensated for {mid} in {comp_time:.4f}s")

        # ----------------------------------------------------------
        # STEP 3d: Combine shares
        # ----------------------------------------------------------
        print(f"  🔸 Combining shares for {chunk_label}...")
        combine_result, combine_time = time_api_call(
            "combine_decryption_shares",
            f"{BASE_URL}/combine_decryption_shares",
            {
                "party_names":     PARTY_NAMES,
                "candidate_names": CANDIDATE_NAMES,
                "joint_public_key":   joint_public_key,
                "commitment_hash":    commitment_hash,
                "ciphertext_tally":   ciphertext_tally,
                "submitted_ballots":  submitted_ballots,
                "guardian_data":      guardian_data,
                "available_guardian_ids":         available_guardian_ids,
                "available_guardian_public_keys": [chunk_shares[g]['guardian_public_key'] for g in available_guardian_ids],
                "available_tally_shares":         [chunk_shares[g]['tally_share']          for g in available_guardian_ids],
                "available_ballot_shares":        [chunk_shares[g]['ballot_shares']        for g in available_guardian_ids],
                "missing_guardian_ids":      miss_ids_flat,
                "compensating_guardian_ids": comp_ids_flat,
                "compensated_tally_shares":  comp_tally_shares,
                "compensated_ballot_shares": comp_ballot_shares,
                "quorum":              quorum,
                "number_of_guardians": number_of_guardians,
            },
        )
        print(f"  ✅ Combined in {combine_time:.4f}s")

        # results arrives as a native dict via msgpack — no json.loads needed
        chunk_results = combine_result['results']
        last_results = chunk_results

        candidates = chunk_results.get('results', {}).get('candidates', {})
        for cid, info in candidates.items():
            final_vote_totals[cid] += int(float(info.get('votes', 0)))

    # ------------------------------------------------------------------
    # STEP 4: Display aggregated final results
    # ------------------------------------------------------------------
    print("\n🔹 STEP 4: Final Aggregated Election Results")
    print("=" * 80)

    if last_results and 'election' in last_results:
        election_info = last_results['election']
        print(f"Election: {election_info.get('name', 'N/A')}")
        print(f"Guardians: {election_info.get('number_of_guardians', NUMBER_OF_GUARDIANS)} total, "
              f"{election_info.get('quorum', QUORUM)} quorum")

    total_votes = sum(final_vote_totals.values())
    print(f"Total ballots cast: {total_votes}")
    print(f"Chunks processed: {len(chunks)}")

    print("\n📊 Vote Counts (aggregated across all chunks):")
    for candidate_id, votes in sorted(final_vote_totals.items()):
        pct = (votes / total_votes * 100) if total_votes else 0
        print(f"  {candidate_id}: {votes} votes ({pct:.2f}%)")

    print("\n✅ ELECTION WORKFLOW COMPLETED SUCCESSFULLY!")

    # Return a dict compatible with the reporting functions
    return {
        'election': last_results.get('election', {}) if last_results else {},
        'results': {
            'total_ballots_cast': total_votes,
            'total_valid_ballots': total_votes,
            'total_spoiled_ballots': 0,
            'candidates': {
                cid: {'votes': votes, 'percentage': f"{(votes / total_votes * 100):.2f}" if total_votes else '0.00'}
                for cid, votes in final_vote_totals.items()
            },
        },
        'chunks': len(chunks),
    }


def main():
    """Run the timed election workflow for multiple ballot counts."""
    print("Starting Election API Performance Test...\n")
    print(f"Testing with ballot counts: {BALLOT_COUNTS}\n")
    
    # Clear the output file at the start
    filename = "election_performance_results.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("ELECTION API PERFORMANCE TEST RESULTS\n")
        f.write(f"Test Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Ballot Counts Tested: {BALLOT_COUNTS}\n")
    
    previous_ballot_count = None
    previous_stats = None
    
    try:
        for ballot_count in BALLOT_COUNTS:
            print("\n" + "🔶" * 50)
            print(f"🔶 TESTING WITH {ballot_count} BALLOTS")
            print("🔶" * 50 + "\n")
            
            # Clear timing and size data for this run
            timing_data.clear()
            size_data.clear()
            
            # Run the complete workflow
            results = run_election_workflow_with_timing(ballot_count)
            
            # Print timing summary
            print_timing_summary()
            
            # Get timing statistics
            stats = get_timing_stats()
            
            # Store results for this ballot count
            all_results[ballot_count] = {
                'stats': stats,
                'results': results
            }
            
            # Export results to file
            export_results_to_file(ballot_count, stats, previous_ballot_count, previous_stats)
            
            # Store for next iteration comparison
            previous_ballot_count = ballot_count
            previous_stats = stats
            
            print(f"\n✅ Completed test for {ballot_count} ballots")
        
        # Print final summary
        print("\n" + "=" * 120)
        print("🎉 ALL PERFORMANCE TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 120)
        print(f"\nResults have been exported to: {filename}")
        print(f"Total ballot counts tested: {len(BALLOT_COUNTS)}")
        print(f"Ballot counts: {BALLOT_COUNTS}")
        print("=" * 120)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = False
    try:
        success = main()
    finally:
        _http_session.close()
    exit(0 if success else 1)