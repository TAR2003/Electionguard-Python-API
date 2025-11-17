#!/usr/bin/env python

import requests
import json
import random
import time
import sys
from typing import Dict, List, Tuple
from collections import defaultdict
from statistics import mean, stdev

# API Base URL
BASE_URL = "http://192.168.0.100:5000"

# Test Configuration - HARDCODED VALUES
NUMBER_OF_GUARDIANS = 5
QUORUM = 3
BALLOT_COUNTS = [64, 128, 256, 512, 1024, 2048]  # Different ballot counts to test
PARTY_NAMES = ["Democratic Alliance", "Progressive Coalition", "Unity Party", "Reform League"]
CANDIDATE_NAMES = ["Alice Johnson", "Bob Smith", "Carol Williams", "David Brown"]

# Output file
OUTPUT_FILE = "dell_result.txt"


class TeeOutput:
    """Class to write output to both console and file simultaneously."""
    def __init__(self, file_path, mode='w'):
        self.terminal = sys.stdout
        self.log = open(file_path, mode, encoding='utf-8')
    
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
    
    def flush(self):
        self.terminal.flush()
        self.log.flush()
    
    def close(self):
        self.log.close()


# Timing tracker
timing_data = defaultdict(list)


def time_api_call(api_name: str, url: str, json_data: dict) -> Tuple[dict, float]:
    """Make an API call and record the response time."""
    start_time = time.time()
    response = requests.post(url, json=json_data)
    end_time = time.time()
    
    elapsed_time = end_time - start_time
    timing_data[api_name].append(elapsed_time)
    
    assert response.status_code == 200, f"{api_name} failed: {response.text}"
    return response.json(), elapsed_time


def find_guardian_data(guardian_id: str, guardian_data_list: List[str], 
                       private_keys_list: List[str], public_keys_list: List[str], 
                       polynomials_list: List[str]) -> Tuple[str, str, str, str]:
    """Find the data for a specific guardian from the lists."""
    
    # Find guardian data
    guardian_data_str = None
    for gd_str in guardian_data_list:
        gd = json.loads(gd_str)
        if gd['id'] == guardian_id:
            guardian_data_str = gd_str
            break
    
    # Find private key
    private_key_str = None
    for pk_str in private_keys_list:
        pk = json.loads(pk_str)
        if pk['guardian_id'] == guardian_id:
            private_key_str = pk_str
            break
    
    # Find public key
    public_key_str = None
    for pk_str in public_keys_list:
        pk = json.loads(pk_str)
        if pk['guardian_id'] == guardian_id:
            public_key_str = pk_str
            break
    
    # Find polynomial
    polynomial_str = None
    for p_str in polynomials_list:
        p = json.loads(p_str)
        if p['guardian_id'] == guardian_id:
            polynomial_str = p_str
            break
    
    if not all([guardian_data_str, private_key_str, public_key_str, polynomial_str]):
        raise ValueError(f"Missing data for guardian {guardian_id}")
    
    return guardian_data_str, private_key_str, public_key_str, polynomial_str


def print_timing_summary():
    """Print a formatted summary of all API timing data."""
    print("\n" + "=" * 100)
    print("API PERFORMANCE SUMMARY")
    print("=" * 100)
    print(f"{'API Endpoint':<40} {'Calls':<10} {'Avg Time':<15} {'Min Time':<15} {'Max Time':<15} {'Std Dev':<15}")
    print("-" * 100)
    
    total_time = 0
    total_calls = 0
    
    for api_name in sorted(timing_data.keys()):
        times = timing_data[api_name]
        num_calls = len(times)
        avg_time = mean(times)
        min_time = min(times)
        max_time = max(times)
        std_dev = stdev(times) if len(times) > 1 else 0.0
        
        total_time += sum(times)
        total_calls += num_calls
        
        print(f"{api_name:<40} {num_calls:<10} {avg_time:<15.4f}s {min_time:<15.4f}s {max_time:<15.4f}s {std_dev:<15.4f}s")
    
    print("-" * 100)
    print(f"{'TOTAL':<40} {total_calls:<10} {total_time:<15.4f}s")
    print("=" * 100)


def run_election_workflow_with_timing(number_of_ballots: int):
    """Run the complete election workflow and measure all API response times."""
    
    print("=" * 100)
    print("ELECTION WORKFLOW PERFORMANCE TEST")
    print("=" * 100)
    print(f"Configuration:")
    print(f"  - Guardians: {NUMBER_OF_GUARDIANS}")
    print(f"  - Quorum: {QUORUM}")
    print(f"  - Ballots: {number_of_ballots}")
    print(f"  - Parties: {len(PARTY_NAMES)}")
    print(f"  - Candidates: {len(CANDIDATE_NAMES)}")
    print("=" * 100)
    
    # STEP 1: Setup Guardians
    print("\n🔹 STEP 1: Setting up guardians...")
    setup_data = {
        "number_of_guardians": NUMBER_OF_GUARDIANS,
        "quorum": QUORUM,
        "party_names": PARTY_NAMES,
        "candidate_names": CANDIDATE_NAMES
    }
    
    setup_result, setup_time = time_api_call(
        "setup_guardians",
        f"{BASE_URL}/setup_guardians",
        setup_data
    )
    
    print(f"✅ Guardian setup completed in {setup_time:.4f}s")
    
    # Extract setup data
    joint_public_key = setup_result['joint_public_key']
    commitment_hash = setup_result['commitment_hash']
    guardian_data = setup_result['guardian_data']
    private_keys = setup_result['private_keys']
    public_keys = setup_result['public_keys']
    polynomials = setup_result['polynomials']
    number_of_guardians = setup_result['number_of_guardians']
    quorum = setup_result['quorum']
    
    # STEP 2: Create and encrypt ballots
    print(f"\n🔹 STEP 2: Creating {number_of_ballots} encrypted ballots...")
    ballot_data = []
    
    for i in range(number_of_ballots):
        chosen_candidate = random.choice(CANDIDATE_NAMES)
        ballot_request = {
            "party_names": PARTY_NAMES,
            "candidate_names": CANDIDATE_NAMES,
            "candidate_name": chosen_candidate,
            "ballot_id": f"ballot-{i+1}",
            "joint_public_key": joint_public_key,
            "commitment_hash": commitment_hash,
            "number_of_guardians": number_of_guardians,
            "quorum": quorum
        }
        
        ballot_result, ballot_time = time_api_call(
            "create_encrypted_ballot",
            f"{BASE_URL}/create_encrypted_ballot",
            ballot_request
        )
        
        ballot_data.append(ballot_result['encrypted_ballot'])
        
        if (i + 1) % 20 == 0:
            print(f"  ✓ Encrypted {i + 1}/{number_of_ballots} ballots...")
    
    print(f"✅ All {number_of_ballots} ballots encrypted")
    
    # STEP 3: Tally encrypted ballots
    print("\n🔹 STEP 3: Tallying encrypted ballots...")
    tally_request = {
        "party_names": PARTY_NAMES,
        "candidate_names": CANDIDATE_NAMES,
        "joint_public_key": joint_public_key,
        "commitment_hash": commitment_hash,
        "encrypted_ballots": ballot_data,
        "number_of_guardians": number_of_guardians,
        "quorum": quorum
    }
    
    tally_result, tally_time = time_api_call(
        "create_encrypted_tally",
        f"{BASE_URL}/create_encrypted_tally",
        tally_request
    )
    
    print(f"✅ Tally created in {tally_time:.4f}s")
    
    ciphertext_tally = tally_result['ciphertext_tally']
    submitted_ballots = tally_result['submitted_ballots']
    
    # STEP 4: Select available and missing guardians for quorum
    print(f"\n🔹 STEP 4: Selecting {QUORUM} out of {NUMBER_OF_GUARDIANS} guardians for quorum decryption...")
    
    # Use first QUORUM guardians as available, rest as missing
    available_guardian_ids = [str(i+1) for i in range(QUORUM)]
    missing_guardian_ids = [str(i+1) for i in range(QUORUM, NUMBER_OF_GUARDIANS)]
    
    print(f"  ✓ Available guardians: {', '.join(available_guardian_ids)}")
    print(f"  ✓ Missing guardians: {', '.join(missing_guardian_ids)}")
    
    # STEP 5: Compute decryption shares for available guardians
    print(f"\n🔹 STEP 5: Computing decryption shares for {len(available_guardian_ids)} available guardians...")
    
    available_guardian_shares = {}
    
    for guardian_id in available_guardian_ids:
        guardian_data_str, private_key_str, public_key_str, polynomial_str = find_guardian_data(
            guardian_id, guardian_data, private_keys, public_keys, polynomials
        )
        
        partial_request = {
            "guardian_id": guardian_id,
            "guardian_data": guardian_data_str,
            "private_key": private_key_str,
            "public_key": public_key_str,
            "polynomial": polynomial_str,
            "party_names": PARTY_NAMES,
            "candidate_names": CANDIDATE_NAMES,
            "ciphertext_tally": ciphertext_tally,
            "submitted_ballots": submitted_ballots,
            "joint_public_key": joint_public_key,
            "commitment_hash": commitment_hash,
            "number_of_guardians": number_of_guardians,
            "quorum": quorum
        }
        
        partial_result, partial_time = time_api_call(
            "create_partial_decryption",
            f"{BASE_URL}/create_partial_decryption",
            partial_request
        )
        
        available_guardian_shares[guardian_id] = {
            'guardian_public_key': partial_result['guardian_public_key'],
            'tally_share': partial_result['tally_share'],
            'ballot_shares': partial_result['ballot_shares']
        }
        
        print(f"  ✓ Guardian {guardian_id} computed shares in {partial_time:.4f}s")
    
    # STEP 6: Compute compensated decryption shares for missing guardians
    print(f"\n🔹 STEP 6: Computing compensated shares for {len(missing_guardian_ids)} missing guardians...")
    
    compensated_shares = {}
    compensation_count = 0
    
    for missing_guardian_id in missing_guardian_ids:
        compensated_shares[missing_guardian_id] = {}
        
        for available_guardian_id in available_guardian_ids:
            available_guardian_data_str, available_private_key_str, available_public_key_str, available_polynomial_str = find_guardian_data(
                available_guardian_id, guardian_data, private_keys, public_keys, polynomials
            )
            
            missing_guardian_data_str, _, _, _ = find_guardian_data(
                missing_guardian_id, guardian_data, private_keys, public_keys, polynomials
            )
            
            compensated_request = {
                "available_guardian_id": available_guardian_id,
                "missing_guardian_id": missing_guardian_id,
                "available_guardian_data": available_guardian_data_str,
                "missing_guardian_data": missing_guardian_data_str,
                "available_private_key": available_private_key_str,
                "available_public_key": available_public_key_str,
                "available_polynomial": available_polynomial_str,
                "party_names": PARTY_NAMES,
                "candidate_names": CANDIDATE_NAMES,
                "ciphertext_tally": ciphertext_tally,
                "submitted_ballots": submitted_ballots,
                "joint_public_key": joint_public_key,
                "commitment_hash": commitment_hash,
                "number_of_guardians": number_of_guardians,
                "quorum": quorum
            }
            
            compensated_result, compensated_time = time_api_call(
                "create_compensated_decryption",
                f"{BASE_URL}/create_compensated_decryption",
                compensated_request
            )
            
            compensated_shares[missing_guardian_id][available_guardian_id] = {
                'compensated_tally_share': compensated_result['compensated_tally_share'],
                'compensated_ballot_shares': compensated_result['compensated_ballot_shares']
            }
            
            compensation_count += 1
            print(f"  ✓ Guardian {available_guardian_id} compensated for {missing_guardian_id} in {compensated_time:.4f}s")
    
    print(f"✅ Completed {compensation_count} compensated decryptions")
    
    # STEP 7: Combine all shares to get final results
    print("\n🔹 STEP 7: Combining all decryption shares...")
    
    # Prepare available guardian shares
    available_guardian_ids_list = []
    available_guardian_public_keys = []
    available_tally_shares = []
    available_ballot_shares = []
    
    for guardian_id, share_data in available_guardian_shares.items():
        available_guardian_ids_list.append(guardian_id)
        available_guardian_public_keys.append(share_data['guardian_public_key'])
        available_tally_shares.append(share_data['tally_share'])
        available_ballot_shares.append(share_data['ballot_shares'])
    
    # Prepare compensated shares
    missing_guardian_ids_list = []
    compensating_guardian_ids_list = []
    compensated_tally_shares = []
    compensated_ballot_shares = []
    
    for missing_guardian_id, compensating_data in compensated_shares.items():
        for available_guardian_id, comp_data in compensating_data.items():
            missing_guardian_ids_list.append(missing_guardian_id)
            compensating_guardian_ids_list.append(available_guardian_id)
            compensated_tally_shares.append(comp_data['compensated_tally_share'])
            compensated_ballot_shares.append(comp_data['compensated_ballot_shares'])
    
    combine_request = {
        "party_names": PARTY_NAMES,
        "candidate_names": CANDIDATE_NAMES,
        "joint_public_key": joint_public_key,
        "commitment_hash": commitment_hash,
        "ciphertext_tally": ciphertext_tally,
        "submitted_ballots": submitted_ballots,
        "guardian_data": guardian_data,
        "available_guardian_ids": available_guardian_ids_list,
        "available_guardian_public_keys": available_guardian_public_keys,
        "available_tally_shares": available_tally_shares,
        "available_ballot_shares": available_ballot_shares,
        "missing_guardian_ids": missing_guardian_ids_list,
        "compensating_guardian_ids": compensating_guardian_ids_list,
        "compensated_tally_shares": compensated_tally_shares,
        "compensated_ballot_shares": compensated_ballot_shares,
        "quorum": quorum,
        "number_of_guardians": number_of_guardians
    }
    
    combine_result, combine_time = time_api_call(
        "combine_decryption_shares",
        f"{BASE_URL}/combine_decryption_shares",
        combine_request
    )
    
    print(f"✅ Combined shares in {combine_time:.4f}s")
    
    results_str = combine_result['results']
    results = json.loads(results_str)
    
    # STEP 8: Display final results
    print("\n🔹 STEP 8: Final Election Results")
    print("=" * 80)
    
    election_info = results['election']
    print(f"Election: {election_info['name']}")
    print(f"Guardians: {election_info['number_of_guardians']} total, {election_info['quorum']} quorum")
    print(f"Total ballots cast: {results['results']['total_ballots_cast']}")
    print(f"Valid ballots: {results['results']['total_valid_ballots']}")
    print(f"Spoiled ballots: {results['results']['total_spoiled_ballots']}")
    
    print("\n📊 Vote Counts:")
    for candidate_id, votes_info in results['results']['candidates'].items():
        print(f"  {candidate_id}: {votes_info['votes']} votes ({votes_info['percentage']}%)")
    
    print("\n✅ ELECTION WORKFLOW COMPLETED SUCCESSFULLY!")
    
    return results


def main():
    """Run the timed election workflow for multiple ballot counts."""
    print("Starting Election API Performance Test...\n")
    print(f"Testing with ballot counts: {BALLOT_COUNTS}\n")
    
    # Clear the output file at the start
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("Election API Performance Test Results\n")
        f.write("=" * 100 + "\n\n")
    
    all_successful = True
    
    try:
        for ballot_count in BALLOT_COUNTS:
            print("\n" + "=" * 100)
            print(f"🚀 STARTING TEST WITH {ballot_count} BALLOTS")
            print("=" * 100 + "\n")
            
            # Open file in append mode for this ballot count test
            tee = TeeOutput(OUTPUT_FILE, mode='a')
            sys.stdout = tee
            
            print("\n" + "=" * 100)
            print(f"🚀 STARTING TEST WITH {ballot_count} BALLOTS")
            print("=" * 100 + "\n")
            
            # Clear timing data for this run
            timing_data.clear()
            
            try:
                # Run the complete workflow
                results = run_election_workflow_with_timing(ballot_count)
                
                # Print timing summary
                print_timing_summary()
                
                print("\n" + "=" * 100)
                print(f"🎉 TEST WITH {ballot_count} BALLOTS COMPLETED SUCCESSFULLY!")
                print("=" * 100 + "\n")
                
            except Exception as e:
                print(f"\n❌ Test with {ballot_count} ballots failed with error: {str(e)}")
                import traceback
                traceback.print_exc()
                all_successful = False
            finally:
                # Restore stdout and close file after each ballot count
                sys.stdout = tee.terminal
                tee.close()
        
        print("\n" + "=" * 100)
        print("🎊 ALL PERFORMANCE TESTS COMPLETED!")
        print("=" * 100)
        print(f"\nResults have been saved to: {OUTPUT_FILE}")
        
        # Append final summary to file
        with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
            f.write("\n" + "=" * 100 + "\n")
            f.write("🎊 ALL PERFORMANCE TESTS COMPLETED!\n")
            f.write("=" * 100 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        all_successful = False
    
    print(f"\n✅ Results saved to {OUTPUT_FILE}")
    
    return all_successful


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)