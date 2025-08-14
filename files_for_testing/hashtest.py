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
    
    number_of_guardians = 3

    joint_public_key = setup_result['joint_public_key']
    commitment_hash = setup_result['commitment_hash']
    manifest = setup_result['manifest']
    guardian_public_keys = setup_result['guardian_public_keys']
    guardian_private_keys = setup_result['guardian_private_keys']
    guardian_polynomials = setup_result['guardian_polynomials']
    
    # print(f"Joint public key: {joint_public_key}")
    # print(f"Commitment hash: {commitment_hash}")
    # print(f"Manifest: {manifest}")
    # print(f"Guardian public keys: {guardian_public_keys}")
    # print(f"Guardian private keys: {guardian_private_keys}")
    # print(f"Guardian polynomials: {guardian_polynomials}")
    print("\nCreating encrypted ballots...")
    encrypted_ballots = []
    ballot_hashes = []
    
    
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
    # print(f"{ballot_result}")
    
    

    
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
        enc  = json.loads(encrypted_ballots[i])
        print(f"🔐 Ballot ID: {enc['object_id']}, Encrypted Hash: {ballot_hashes[i]}")
    
    
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
    ciphertext_tally = tally_result['ciphertext_tally']
    submitted_ballots = tally_result['submitted_ballots']
    # print(tally_result)
    
    new_ballot_hashes = []
    q_data = {
        "encrypted_ballots": submitted_ballots
    }
    q_response = requests.post(f"{BASE_URL}/get_ballot_hashes", json=q_data)
    new_ballot_hashes = (q_response.json()['ballot_hashes'])
    print(f"New Ballot Hashes: {new_ballot_hashes}")
    print(f"Ballot Hashes: {ballot_hashes}")
    

    

if __name__ == "__main__":
    results = test_election_workflow()
    
    with open("election_results.json", "w") as f:
        json.dump(results, f, indent=2)