#!/usr/bin/env python

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from services.benaloh_challenge import benaloh_challenge_service

def test_benaloh_service():
    """Test the Benaloh challenge service directly."""
    
    # Load test data
    try:
        with open('create_encrypted_ballot_response.json', 'r') as f:
            ballot_response = json.load(f)
    except FileNotFoundError:
        print("❌ Error: create_encrypted_ballot_response.json not found.")
        print("Please ensure the file exists.")
        return
    
    try:
        with open('io/create_encrypted_ballot_request.json', 'r') as f:
            original_request = json.load(f)
    except FileNotFoundError:
        print("❌ Error: create_encrypted_ballot_request.json not found.")
        return
    
    encrypted_ballot_with_nonce = ballot_response.get('encrypted_ballot_with_nonce')
    if not encrypted_ballot_with_nonce:
        print("❌ Error: No encrypted_ballot_with_nonce found in response file.")
        return
    
    print("🔍 Testing Benaloh challenge service...")
    print(f"Expected candidate: {original_request['candidate_name']}")
    
    # Test with correct candidate
    try:
        result = benaloh_challenge_service(
            encrypted_ballot_with_nonce=encrypted_ballot_with_nonce,
            party_names=original_request["party_names"],
            candidate_names=original_request["candidate_names"],
            candidate_name=original_request["candidate_name"],  # Correct candidate
            joint_public_key=original_request["joint_public_key"],
            commitment_hash=original_request["commitment_hash"],
            number_of_guardians=original_request["number_of_guardians"],
            quorum=original_request["quorum"]
        )
        
        print(f"✅ Service result: {result}")
        
        if result['success']:
            if result['match']:
                print("🎉 SUCCESS: Correct candidate correctly verified!")
            else:
                print("❌ UNEXPECTED: Expected match=true for correct candidate")
        else:
            print(f"❌ Service error: {result['error']}")
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60 + "\n")
    
    # Test with incorrect candidate
    incorrect_candidate = None
    for candidate in original_request["candidate_names"]:
        if candidate != original_request["candidate_name"]:
            incorrect_candidate = candidate
            break
    
    if not incorrect_candidate:
        print("❌ Could not find alternative candidate for testing.")
        return
        
    print(f"🔍 Testing with incorrect candidate: {incorrect_candidate}")
    
    try:
        result2 = benaloh_challenge_service(
            encrypted_ballot_with_nonce=encrypted_ballot_with_nonce,
            party_names=original_request["party_names"],
            candidate_names=original_request["candidate_names"],
            candidate_name=incorrect_candidate,  # Wrong candidate
            joint_public_key=original_request["joint_public_key"],
            commitment_hash=original_request["commitment_hash"],
            number_of_guardians=original_request["number_of_guardians"],
            quorum=original_request["quorum"]
        )
        
        print(f"✅ Service result: {result2}")
        
        if result2['success']:
            if not result2['match']:
                print("🎉 SUCCESS: Incorrect candidate correctly rejected!")
            else:
                print("❌ UNEXPECTED: Expected match=false for incorrect candidate")
        else:
            print(f"❌ Service error: {result2['error']}")
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_benaloh_service()