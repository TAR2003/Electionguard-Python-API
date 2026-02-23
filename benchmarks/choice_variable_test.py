#!/usr/bin/env python

import requests
import json
import random
import time
from typing import Dict, List, Tuple
from collections import defaultdict
from statistics import mean, stdev

import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API Base URL
BASE_URL = "http://192.168.30.138:5000"

# Test Configuration
NUMBER_OF_GUARDIANS = 5
QUORUM = 3
TOTAL_BALLOTS = 500
BALLOTS_PER_CHOICE = 100  # 500 ballots / 5 candidates = 100 ballots per candidate
PARTY_NAMES = ["Democratic Alliance", "Progressive Coalition", "Unity Party", "Reform League", "Green Movement"]
# 5 candidates, each belonging to a separate party
CANDIDATE_NAMES = ["Nobo", "Dipanta Nobo", "Dipanta Kumar Roy Nobo", "Dipanta 2005074 Kumar 2005074 Roy Nobo", "Prabhakarna Sripalawardhana Atapattu Jayasuriya Laxmansriramkrishna Shivavenkata Rajasekhara Shrinivasana Trichipalli Yekya Parampeel Parambatur Chinnaswami Muthuswami Venugopal Iyer Dipanta Kumar Roy Nobo"]

# Data tracking
choice_data = defaultdict(lambda: {
    'ballot_ids': [],
    'encryption_times': [],
    'request_sizes': [],
    'response_sizes': []
})


def format_size(size_bytes: int) -> str:
    """Format size in bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f}TB"


def setup_guardians_and_get_keys():
    """Setup guardians and get joint public key and commitment hash."""
    print("\n🔹 Setting up guardians...")
    setup_data = {
        "number_of_guardians": NUMBER_OF_GUARDIANS,
        "quorum": QUORUM,
        "party_names": PARTY_NAMES,
        "candidate_names": CANDIDATE_NAMES
    }
    
    start_time = time.time()
    response = requests.post(
        f"{BASE_URL}/setup_guardians",
        json=setup_data,
        verify=False,
        timeout=None
    )
    end_time = time.time()
    
    assert response.status_code == 200, f"Guardian setup failed: {response.text}"
    
    result = response.json()
    elapsed_time = end_time - start_time
    
    print(f"✅ Guardian setup completed in {elapsed_time:.4f}s")
    
    return {
        'joint_public_key': result['joint_public_key'],
        'commitment_hash': result['commitment_hash'],
        'number_of_guardians': result['number_of_guardians'],
        'quorum': result['quorum'],
        'setup_time': elapsed_time
    }


def create_encrypted_ballot(candidate_name: str, ballot_id: str, election_keys: dict) -> Tuple[float, int, int]:
    """
    Create an encrypted ballot and return timing and size information.
    
    Returns:
        Tuple of (elapsed_time, request_size, response_size)
    """
    ballot_request = {
        "party_names": PARTY_NAMES,
        "candidate_names": CANDIDATE_NAMES,
        "candidate_name": candidate_name,
        "ballot_id": ballot_id,
        "joint_public_key": election_keys['joint_public_key'],
        "commitment_hash": election_keys['commitment_hash'],
        "number_of_guardians": election_keys['number_of_guardians'],
        "quorum": election_keys['quorum']
    }
    
    # Calculate request size
    request_json = json.dumps(ballot_request)
    request_size = len(request_json.encode('utf-8'))
    
    # Make API call
    start_time = time.time()
    response = requests.post(
        f"{BASE_URL}/create_encrypted_ballot",
        json=ballot_request,
        verify=False,
        timeout=None
    )
    end_time = time.time()
    
    # Calculate response size
    response_size = len(response.content)
    elapsed_time = end_time - start_time
    
    assert response.status_code == 200, f"Ballot encryption failed: {response.text}"
    
    return elapsed_time, request_size, response_size


def assign_ballots_to_choices():
    """
    Assign 100 ballots to 5 choices, with exactly 20 ballots per choice.
    Returns a list of tuples: [(ballot_id, candidate_name), ...]
    """
    assignments = []
    ballot_counter = 1
    
    for candidate in CANDIDATE_NAMES:
        for _ in range(BALLOTS_PER_CHOICE):
            ballot_id = f"ballot-{ballot_counter}"
            assignments.append((ballot_id, candidate))
            ballot_counter += 1
    
    # Shuffle to randomize the order of ballot creation
    random.shuffle(assignments)
    
    return assignments


def run_choice_encryption_test():
    """Run the encryption test with 5 choices, 20 ballots each."""
    
    print("=" * 100)
    print("CHOICE-BASED BALLOT ENCRYPTION TEST")
    print("=" * 100)
    print(f"Configuration:")
    print(f"  - Guardians: {NUMBER_OF_GUARDIANS}")
    print(f"  - Quorum: {QUORUM}")
    print(f"  - Total Ballots: {TOTAL_BALLOTS}")
    print(f"  - Choices (Candidates): {len(CANDIDATE_NAMES)}")
    print(f"  - Ballots per Choice: {BALLOTS_PER_CHOICE}")
    print("=" * 100)
    
    # STEP 1: Setup guardians
    election_keys = setup_guardians_and_get_keys()
    
    # STEP 2: Assign ballots to choices
    print(f"\n🔹 Assigning {TOTAL_BALLOTS} ballots to {len(CANDIDATE_NAMES)} choices...")
    ballot_assignments = assign_ballots_to_choices()
    print(f"✅ Ballot assignments created (randomized order)")
    
    # STEP 3: Create encrypted ballots
    print(f"\n🔹 Creating {TOTAL_BALLOTS} encrypted ballots...")
    
    for idx, (ballot_id, candidate_name) in enumerate(ballot_assignments, 1):
        # Encrypt the ballot
        encryption_time, request_size, response_size = create_encrypted_ballot(
            candidate_name, ballot_id, election_keys
        )
        
        # Store data for this choice
        choice_data[candidate_name]['ballot_ids'].append(ballot_id)
        choice_data[candidate_name]['encryption_times'].append(encryption_time)
        choice_data[candidate_name]['request_sizes'].append(request_size)
        choice_data[candidate_name]['response_sizes'].append(response_size)
        
        # Progress update
        if idx % 10 == 0:
            print(f"  ✓ Encrypted {idx}/{TOTAL_BALLOTS} ballots...")
    
    print(f"✅ All {TOTAL_BALLOTS} ballots encrypted successfully")
    
    # STEP 4: Calculate and display statistics
    print("\n🔹 Calculating statistics per choice...")
    calculate_and_display_statistics()
    
    # STEP 5: Export results to file
    export_results_to_file(election_keys['setup_time'])
    
    print("\n✅ CHOICE ENCRYPTION TEST COMPLETED SUCCESSFULLY!")


def calculate_and_display_statistics():
    """Calculate and display average encryption time and size per choice."""
    print("\n" + "=" * 120)
    print("ENCRYPTION STATISTICS BY CHOICE")
    print("=" * 120)
    print(f"{'Choice (Candidate)':<30} {'Ballots':<10} {'Avg Time':<15} {'Avg Req Size':<15} {'Avg Resp Size':<15}")
    print("-" * 120)
    
    for candidate in CANDIDATE_NAMES:
        data = choice_data[candidate]
        num_ballots = len(data['ballot_ids'])
        avg_time = mean(data['encryption_times']) if data['encryption_times'] else 0
        avg_req_size = mean(data['request_sizes']) if data['request_sizes'] else 0
        avg_resp_size = mean(data['response_sizes']) if data['response_sizes'] else 0
        
        print(f"{candidate:<30} {num_ballots:<10} {avg_time:<15.4f}s {format_size(avg_req_size):<15} {format_size(avg_resp_size):<15}")
    
    print("=" * 120)


def export_results_to_file(setup_time: float):
    """Export detailed results to a text file."""
    filename = "choice_encryption_results.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=" * 150 + "\n")
        f.write("CHOICE-BASED BALLOT ENCRYPTION TEST RESULTS\n")
        f.write("=" * 150 + "\n")
        f.write(f"Test Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"\nConfiguration:\n")
        f.write(f"  - Guardians: {NUMBER_OF_GUARDIANS}\n")
        f.write(f"  - Quorum: {QUORUM}\n")
        f.write(f"  - Total Ballots: {TOTAL_BALLOTS}\n")
        f.write(f"  - Choices (Candidates): {len(CANDIDATE_NAMES)}\n")
        f.write(f"  - Ballots per Choice: {BALLOTS_PER_CHOICE}\n")
        f.write(f"  - Guardian Setup Time: {setup_time:.4f}s\n")
        
        f.write("\n" + "=" * 150 + "\n")
        f.write("ENCRYPTION STATISTICS BY CHOICE\n")
        f.write("=" * 150 + "\n")
        f.write(f"{'Choice (Candidate)':<30} {'Ballots':<10} {'Avg Time':<15} {'Min Time':<15} {'Max Time':<15} {'Std Dev':<15} {'Avg Req Size':<15} {'Avg Resp Size':<15}\n")
        f.write("-" * 150 + "\n")
        
        for candidate in CANDIDATE_NAMES:
            data = choice_data[candidate]
            num_ballots = len(data['ballot_ids'])
            
            if data['encryption_times']:
                avg_time = mean(data['encryption_times'])
                min_time = min(data['encryption_times'])
                max_time = max(data['encryption_times'])
                std_dev = stdev(data['encryption_times']) if len(data['encryption_times']) > 1 else 0.0
            else:
                avg_time = min_time = max_time = std_dev = 0
            
            avg_req_size = mean(data['request_sizes']) if data['request_sizes'] else 0
            avg_resp_size = mean(data['response_sizes']) if data['response_sizes'] else 0
            
            f.write(f"{candidate:<30} {num_ballots:<10} {avg_time:<15.4f}s {min_time:<15.4f}s {max_time:<15.4f}s {std_dev:<15.4f}s {format_size(avg_req_size):<15} {format_size(avg_resp_size):<15}\n")
        
        f.write("=" * 150 + "\n\n")
        
        # Detailed ballot assignments per choice
        f.write("DETAILED BALLOT ASSIGNMENTS\n")
        f.write("=" * 150 + "\n")
        
        for candidate in CANDIDATE_NAMES:
            data = choice_data[candidate]
            f.write(f"\nChoice: {candidate}\n")
            f.write(f"Ballot Count: {len(data['ballot_ids'])}\n")
            f.write(f"Ballot IDs: {', '.join(data['ballot_ids'])}\n")
            f.write("-" * 150 + "\n")
        
        # Overall statistics
        f.write("\n" + "=" * 150 + "\n")
        f.write("OVERALL STATISTICS\n")
        f.write("=" * 150 + "\n")
        
        all_times = []
        all_req_sizes = []
        all_resp_sizes = []
        
        for candidate in CANDIDATE_NAMES:
            data = choice_data[candidate]
            all_times.extend(data['encryption_times'])
            all_req_sizes.extend(data['request_sizes'])
            all_resp_sizes.extend(data['response_sizes'])
        
        if all_times:
            f.write(f"Total Ballots Encrypted: {len(all_times)}\n")
            f.write(f"Total Encryption Time: {sum(all_times):.4f}s\n")
            f.write(f"Average Encryption Time per Ballot: {mean(all_times):.4f}s\n")
            f.write(f"Min Encryption Time: {min(all_times):.4f}s\n")
            f.write(f"Max Encryption Time: {max(all_times):.4f}s\n")
            f.write(f"Std Dev Encryption Time: {stdev(all_times):.4f}s\n")
            f.write(f"\nAverage Request Size per Ballot: {format_size(mean(all_req_sizes))}\n")
            f.write(f"Average Response Size per Ballot: {format_size(mean(all_resp_sizes))}\n")
            f.write(f"Total Request Data: {format_size(sum(all_req_sizes))}\n")
            f.write(f"Total Response Data: {format_size(sum(all_resp_sizes))}\n")
        
        f.write("\n" + "=" * 150 + "\n")
    
    print(f"\n📄 Detailed results exported to {filename}")


def main():
    """Main entry point for the choice encryption test."""
    print("\nStarting Choice-Based Ballot Encryption Test...\n")
    
    try:
        run_choice_encryption_test()
        return True
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
