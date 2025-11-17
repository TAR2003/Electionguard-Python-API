#!/usr/bin/env python

import requests
import json
import random
import time
from typing import Dict, List, Tuple
from collections import defaultdict

# API Base URL
BASE_URL = "http://localhost:5000"

# Timing statistics storage
timing_stats = defaultdict(list)

def time_api_call(endpoint_name: str, func):
    """Decorator-like function to time API calls"""
    start_time = time.time()
    result = func()
    end_time = time.time()
    elapsed = end_time - start_time
    timing_stats[endpoint_name].append(elapsed)
    return result

def find_guardian_data(guardian_id: str, guardian_data_list: List[str], 
                       private_keys_list: List[str], public_keys_list: List[str], 
                       polynomials_list: List[str]) -> Tuple[str, str, str, str]:
    """Find the data for a specific guardian from the lists."""
    guardian_data_str = None
    for gd_str in guardian_data_list:
        gd = json.loads(gd_str)
        if gd['id'] == guardian_id:
            guardian_data_str = gd_str
            break
    
    private_key_str = None
    for pk_str in private_keys_list:
        pk = json.loads(pk_str)
        if pk['guardian_id'] == guardian_id:
            private_key_str = pk_str
            break
    
    public_key_str = None
    for pk_str in public_keys_list:
        pk = json.loads(pk_str)
        if pk['guardian_id'] == guardian_id:
            public_key_str = pk_str
            break
    
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
    """Print detailed timing statistics for all API endpoints"""
    print("\n" + "=" * 100)
    print("📊 API PERFORMANCE SUMMARY")
    print("=" * 100)
    
    total_time = 0
    
    for endpoint, times in sorted(timing_stats.items()):
        count = len(times)
        avg_time = sum(times) / count
        min_time = min(times)
        max_time = max(times)
        total_endpoint_time = sum(times)
        
        total_time += total_endpoint_time
        
        print(f"\n📌 {endpoint}")
        print(f"   Calls: {count}")
        print(f"   Average: {avg_time:.4f}s")
        print(f"   Min: {min_time:.4f}s")
        print(f"   Max: {max_time:.4f}s")
        print(f"   Total: {total_endpoint_time:.4f}s")
    
    print("\n" + "=" * 100)
    print(f"🕒 TOTAL API TIME: {total_time:.4f}s")
    print("=" * 100 + "\n")

def test_election_with_timing():
    """Test the complete election workflow with detailed timing measurements"""
    
    # Hard-coded test configuration
    NUM_GUARDIANS = 5
    QUORUM = 3
    NUM_BALLOTS = 100
    PARTY_NAMES = ["Democratic Party", "Republican Party", "Independent Party", "Green Party"]
    CANDIDATE_NAMES = ["Alice Johnson", "Bob Smith", "Carol Williams", "David Brown", "Eve Davis", "Frank Miller"]
    
    print("=" * 100)
    print("🚀 STARTING ELECTION WORKFLOW WITH PERFORMANCE TIMING")
    print("=" * 100)
    print(f"\n📋 Configuration:")
    print(f"   Guardians: {NUM_GUARDIANS}")
    print(f"   Quorum: {QUORUM}")
    print(f"   Ballots to create: {NUM_BALLOTS}")
    print(f"   Parties: {len(PARTY_NAMES)}")
    print(f"   Candidates: {len(CANDIDATE_NAMES)}")
    
    # ========================================================================
    # STEP 1: Setup Guardians
    # ========================================================================
    print("\n" + "-" * 100)
    print("🔹 STEP 1: Setting up guardians")
    print("-" * 100)
    
    setup_data = {
        "number_of_guardians": NUM_GUARDIANS,
        "quorum": QUORUM,
        "party_names": PARTY_NAMES,
        "candidate_names": CANDIDATE_NAMES
    }
    
    def setup_guardians_call():
        response = requests.post(f"{BASE_URL}/setup_guardians", json=setup_data)
        assert response.status_code == 200, f"Guardian setup failed: {response.text}"
        return response.json()
    
    setup_result = time_api_call("/setup_guardians", setup_guardians_call)
    
    print(f"✅ Created {NUM_GUARDIANS} guardians with quorum of {QUORUM}")
    print(f"✅ Time taken: {timing_stats['/setup_guardians'][0]:.4f}s")
    
    # Extract setup data
    joint_public_key = setup_result['joint_public_key']
    commitment_hash = setup_result['commitment_hash']
    manifest = setup_result['manifest']
    guardian_data = setup_result['guardian_data']
    private_keys = setup_result['private_keys']
    public_keys = setup_result['public_keys']
    polynomials = setup_result['polynomials']
    number_of_guardians = setup_result['number_of_guardians']
    quorum = setup_result['quorum']
    
    # Debug output
    print(f"✅ Joint public key length: {len(joint_public_key) if joint_public_key else 'None'}")
    print(f"✅ Commitment hash length: {len(commitment_hash) if commitment_hash else 'None'}")
    print(f"✅ Number of guardians: {number_of_guardians}")
    print(f"✅ Quorum: {quorum}")
    
    # ========================================================================
    # STEP 2: Create and encrypt ballots
    # ========================================================================
    print("\n" + "-" * 100)
    print(f"🔹 STEP 2: Creating and encrypting {NUM_BALLOTS} ballots")
    print("-" * 100)
    
    ballot_data = []
    
    for i in range(NUM_BALLOTS):
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
        
        # Debug: print the first ballot request to check values
        if i == 0:
            print(f"\n🔍 DEBUG - First ballot request:")
            print(f"   ballot_id: {ballot_request['ballot_id']}")
            print(f"   candidate_name: {ballot_request['candidate_name']}")
            print(f"   joint_public_key type: {type(joint_public_key)}, length: {len(joint_public_key) if joint_public_key else 'None'}")
            print(f"   commitment_hash type: {type(commitment_hash)}, length: {len(commitment_hash) if commitment_hash else 'None'}")
            print(f"   number_of_guardians: {number_of_guardians} (type: {type(number_of_guardians)})")
            print(f"   quorum: {quorum} (type: {type(quorum)})")
            print(f"   party_names: {PARTY_NAMES}")
            print(f"   candidate_names: {CANDIDATE_NAMES}\n")
        
        def create_ballot_call():
            response = requests.post(f"{BASE_URL}/create_encrypted_ballot", json=ballot_request)
            assert response.status_code == 200, f"Ballot encryption failed: {response.text}"
            return response.json()
        
        ballot_result = time_api_call("/create_encrypted_ballot", create_ballot_call)
        ballot_data.append(ballot_result['encrypted_ballot'])
        
        if (i + 1) % 20 == 0 or (i + 1) == NUM_BALLOTS:
            avg_so_far = sum(timing_stats['/create_encrypted_ballot']) / len(timing_stats['/create_encrypted_ballot'])
            print(f"   Progress: {i+1}/{NUM_BALLOTS} ballots created (avg: {avg_so_far:.4f}s per ballot)")
    
    print(f"✅ All {NUM_BALLOTS} ballots encrypted successfully")
    
    # ========================================================================
    # STEP 3: Tally encrypted ballots
    # ========================================================================
    print("\n" + "-" * 100)
    print("🔹 STEP 3: Tallying encrypted ballots")
    print("-" * 100)
    
    tally_request = {
        "party_names": PARTY_NAMES,
        "candidate_names": CANDIDATE_NAMES,
        "joint_public_key": joint_public_key,
        "commitment_hash": commitment_hash,
        "encrypted_ballots": ballot_data,
        "number_of_guardians": number_of_guardians,
        "quorum": quorum
    }
    
    def create_tally_call():
        response = requests.post(f"{BASE_URL}/create_encrypted_tally", json=tally_request)
        assert response.status_code == 200, f"Tally creation failed: {response.text}"
        return response.json()
    
    tally_result = time_api_call("/create_encrypted_tally", create_tally_call)
    
    ciphertext_tally = tally_result['ciphertext_tally']
    submitted_ballots = tally_result['submitted_ballots']
    
    print(f"✅ Tally created with {len(submitted_ballots)} ballots")
    print(f"✅ Time taken: {timing_stats['/create_encrypted_tally'][0]:.4f}s")
    
    # ========================================================================
    # STEP 4: Select guardians for quorum decryption
    # ========================================================================
    print("\n" + "-" * 100)
    print("🔹 STEP 4: Selecting guardians for quorum decryption")
    print("-" * 100)
    
    # Use exactly QUORUM guardians as available
    available_guardian_ids = [str(i+1) for i in range(QUORUM)]
    missing_guardian_ids = [str(i+1) for i in range(QUORUM, NUM_GUARDIANS)]
    
    print(f"✅ Selected {len(available_guardian_ids)} available guardians: {available_guardian_ids}")
    print(f"✅ Missing {len(missing_guardian_ids)} guardians (to be compensated): {missing_guardian_ids}")
    
    # ========================================================================
    # STEP 5: Compute decryption shares for available guardians
    # ========================================================================
    print("\n" + "-" * 100)
    print("🔹 STEP 5: Computing decryption shares for available guardians")
    print("-" * 100)
    
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
        
        def create_partial_call():
            response = requests.post(f"{BASE_URL}/create_partial_decryption", json=partial_request)
            assert response.status_code == 200, f"Partial decryption failed: {response.text}"
            return response.json()
        
        partial_result = time_api_call("/create_partial_decryption", create_partial_call)
        
        available_guardian_shares[guardian_id] = {
            'guardian_public_key': partial_result['guardian_public_key'],
            'tally_share': partial_result['tally_share'],
            'ballot_shares': partial_result['ballot_shares']
        }
        print(f"✅ Guardian {guardian_id} computed decryption shares (time: {timing_stats['/create_partial_decryption'][-1]:.4f}s)")
    
    # ========================================================================
    # STEP 6: Compute compensated decryption shares for missing guardians
    # ========================================================================
    print("\n" + "-" * 100)
    print("🔹 STEP 6: Computing compensated decryption shares")
    print("-" * 100)
    
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
            
            def create_compensated_call():
                response = requests.post(f"{BASE_URL}/create_compensated_decryption", json=compensated_request)
                assert response.status_code == 200, f"Compensated decryption failed: {response.text}"
                return response.json()
            
            compensated_result = time_api_call("/create_compensated_decryption", create_compensated_call)
            
            compensated_shares[missing_guardian_id][available_guardian_id] = {
                'compensated_tally_share': compensated_result['compensated_tally_share'],
                'compensated_ballot_shares': compensated_result['compensated_ballot_shares']
            }
            
            compensation_count += 1
            if compensation_count % 5 == 0 or compensation_count == len(missing_guardian_ids) * len(available_guardian_ids):
                avg_so_far = sum(timing_stats['/create_compensated_decryption']) / len(timing_stats['/create_compensated_decryption'])
                print(f"   Progress: {compensation_count}/{len(missing_guardian_ids) * len(available_guardian_ids)} compensations (avg: {avg_so_far:.4f}s)")
    
    print(f"✅ Computed all compensated shares for {len(missing_guardian_ids)} missing guardians")
    
    # ========================================================================
    # STEP 7: Combine all shares to get final results
    # ========================================================================
    print("\n" + "-" * 100)
    print("🔹 STEP 7: Combining shares to get final results")
    print("-" * 100)
    
    # Prepare separate arrays for available guardian shares
    available_guardian_ids_list = []
    available_guardian_public_keys = []
    available_tally_shares = []
    available_ballot_shares = []
    
    for guardian_id, share_data in available_guardian_shares.items():
        available_guardian_ids_list.append(guardian_id)
        available_guardian_public_keys.append(share_data['guardian_public_key'])
        available_tally_shares.append(share_data['tally_share'])
        available_ballot_shares.append(share_data['ballot_shares'])
    
    # Prepare separate arrays for compensated shares
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
    
    def combine_shares_call():
        response = requests.post(f"{BASE_URL}/combine_decryption_shares", json=combine_request)
        assert response.status_code == 200, f"Share combination failed: {response.text}"
        return response.json()
    
    combine_result = time_api_call("/combine_decryption_shares", combine_shares_call)
    
    results_str = combine_result['results']
    results = json.loads(results_str)
    
    print(f"✅ Successfully decrypted election with {quorum} out of {number_of_guardians} guardians")
    print(f"✅ Time taken: {timing_stats['/combine_decryption_shares'][0]:.4f}s")
    
    # ========================================================================
    # STEP 8: Display final results
    # ========================================================================
    print("\n" + "-" * 100)
    print("🔹 STEP 8: Final Election Results")
    print("-" * 100)
    
    election_info = results['election']
    print(f"\n📊 Election: {election_info['name']}")
    print(f"   Guardians: {election_info['number_of_guardians']} total, {election_info['quorum']} quorum")
    print(f"   Total ballots cast: {results['results']['total_ballots_cast']}")
    print(f"   Valid ballots: {results['results']['total_valid_ballots']}")
    print(f"   Spoiled ballots: {results['results']['total_spoiled_ballots']}")
    
    print("\n📈 Vote Counts:")
    for candidate_id, votes_info in results['results']['candidates'].items():
        print(f"   {candidate_id}: {votes_info['votes']} votes ({votes_info['percentage']}%)")
    
    print("\n✅ ELECTION WORKFLOW COMPLETED SUCCESSFULLY!")
    
    return results

def main():
    """Run the timing test"""
    print("\n" + "=" * 100)
    print("🎯 ELECTIONGUARD API PERFORMANCE TIMING TEST")
    print("=" * 100)
    
    try:
        # Clear timing stats
        timing_stats.clear()
        
        # Run the election workflow with timing
        test_election_with_timing()
        
        # Print comprehensive timing summary
        print_timing_summary()
        
        print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Print timing summary even if test failed
        if timing_stats:
            print("\n⚠️  Partial timing data before failure:")
            print_timing_summary()
        
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
