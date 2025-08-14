#!/usr/bin/env python

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:5000"

def test_election_workflow():
    # 1. Setup Guardians
    setup_data = {
        "number_of_guardians": 3,
        "quorum": 3,
        "party_names": ["Party A", "Party B"],
        "candidate_names": ["Candidate 1", "Candidate 2"]
    }
    setup_response = requests.post(f"{BASE_URL}/setup_guardians", json=setup_data)
    assert setup_response.status_code == 200, "Guardian setup failed"
    setup_result = setup_response.json()
    
    number_of_guardians = setup_result['number_of_guardians']
    quorum = setup_result['quorum']
    
    joint_public_key = setup_result['joint_public_key']
    commitment_hash = setup_result['commitment_hash']
    manifest = setup_result['manifest']
    guardian_data = [json.loads(g) if isinstance(g, str) else g for g in setup_result['guardian_data']]
    
    print(f"✅ Set up {number_of_guardians} guardians with quorum={quorum}")
    
    print("\nCreating encrypted ballots...")
    encrypted_ballots = []
    ballot_hashes = []
    
    # Create ballot for Candidate 1
    ballot_data = {
        "party_names": ["Party A", "Party B"],
        "candidate_names": ["Candidate 1", "Candidate 2"],
        "candidate_name": "Candidate 1",
        "ballot_id": f"ballot-masnoon",
        "joint_public_key": joint_public_key,
        "commitment_hash": commitment_hash
    }
    ballot_response = requests.post(f"{BASE_URL}/create_encrypted_ballot", json=ballot_data)
    assert ballot_response.status_code == 200, "Ballot creation failed"
    ballot_result = ballot_response.json()
    encrypted_ballots.append(ballot_result['encrypted_ballot'])
    ballot_hashes.append(ballot_result['ballot_hash'])
    
    # Create ballot for Candidate 2
    ballot_data = {
        "party_names": ["Party A", "Party B"],
        "candidate_names": ["Candidate 1", "Candidate 2"],
        "candidate_name": "Candidate 2",
        "ballot_id": f"ballot-tawkir",
        "joint_public_key": joint_public_key,
        "commitment_hash": commitment_hash
    }
    ballot_response = requests.post(f"{BASE_URL}/create_encrypted_ballot", json=ballot_data)
    assert ballot_response.status_code == 200, "Ballot creation failed"
    ballot_result = ballot_response.json()
    encrypted_ballots.append(ballot_result['encrypted_ballot'])
    ballot_hashes.append(ballot_result['ballot_hash'])

    for i in range(len(encrypted_ballots)):
        enc = json.loads(encrypted_ballots[i]) if isinstance(encrypted_ballots[i], str) else encrypted_ballots[i]
        print(f"🔐 Ballot ID: {enc['object_id']}, Encrypted Hash: {ballot_hashes[i]}")
    
    # 2. Create encrypted tally
    tally_data = {
        "party_names": ["Party A", "Party B"],
        "candidate_names": ["Candidate 1", "Candidate 2"],
        "joint_public_key": joint_public_key,
        "commitment_hash": commitment_hash,
        "encrypted_ballots": encrypted_ballots
    }
    tally_response = requests.post(f"{BASE_URL}/create_encrypted_tally", json=tally_data)
    assert tally_response.status_code == 200, "Tally creation failed"
    tally_result = tally_response.json()
    ciphertext_tally = json.loads(tally_result['ciphertext_tally']) if isinstance(tally_result['ciphertext_tally'], str) else tally_result['ciphertext_tally']
    submitted_ballots = [json.loads(b) if isinstance(b, str) else b for b in tally_result['submitted_ballots']]
    print(f"✅ Tally created with {len(submitted_ballots)} ballots")
    
    # 3. Calculate partial decryption shares for all guardians
    print("\nComputing partial decryption shares...")
    available_guardian_shares = {}
    
    for guardian in guardian_data:
        partial_request = {
            "guardian_id": guardian['id'],
            "guardian_data": [json.dumps(g) for g in guardian_data],
            "party_names": setup_data['party_names'],
            "candidate_names": setup_data['candidate_names'],
            "ciphertext_tally": json.dumps(ciphertext_tally),
            "submitted_ballots": [json.dumps(b) for b in submitted_ballots],
            "joint_public_key": joint_public_key,
            "commitment_hash": commitment_hash
        }
        partial_response = requests.post(f"{BASE_URL}/create_partial_decryption", json=partial_request)
        assert partial_response.status_code == 200, f"Partial decryption failed for guardian {guardian['id']}: {partial_response.text}"
        partial_result = partial_response.json()
        available_guardian_shares[guardian['id']] = {
            'guardian_public_key': partial_result['guardian_public_key'],
            'tally_share': partial_result['tally_share'],
            'ballot_shares': partial_result['ballot_shares']
        }
        print(f"✅ Guardian {guardian['id']} computed decryption shares")
    
    # Since we have all guardians available, no compensated shares needed
    compensated_shares = {}
    
    # 4. Combine decryptions and get results
    print("\nCombining decryptions...")
    combine_data = {
        "party_names": setup_data['party_names'],
        "candidate_names": setup_data['candidate_names'],
        "joint_public_key": joint_public_key,
        "commitment_hash": commitment_hash,
        "ciphertext_tally": json.dumps(ciphertext_tally),
        "submitted_ballots": [json.dumps(b) for b in submitted_ballots],
        "guardian_data": [json.dumps(g) for g in guardian_data],
        "available_guardian_shares": available_guardian_shares,
        "compensated_shares": compensated_shares,
        "quorum": quorum
    }
    
    combine_response = requests.post(f"{BASE_URL}/combine_decryption_shares", json=combine_data)
    assert combine_response.status_code == 200, "Combining decryptions failed"
    final_results = combine_response.json()
    print("Final results obtained!")
    
    print("\n=== ELECTION RESULTS ===")
    print(f"Valid ballots: {final_results['results']['results']['total_valid_ballots']}")
    print(f"Spoiled ballots: {final_results['results']['results']['total_spoiled_ballots']}")
    
    print("\nCandidate Results:")
    for candidate, result in final_results['results']['results']['candidates'].items():
        print(f"  {candidate}: {result['votes']} votes ({result['percentage']}%)")
    
    print("\nVerification Status:")
    for ballot in final_results['results']['verification']['ballots']:
        print(f"  Ballot {ballot['ballot_id']}: {ballot['status']} - {ballot['verification']}")
    
    return final_results

if __name__ == "__main__":
    results = test_election_workflow()
    
    with open("election_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\nResults saved to election_results.json")
