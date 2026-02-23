#!/usr/bin/env python

import requests
import json
import sys

# API Base URL
BASE_URL = "http://localhost:5000"

def test_benaloh_challenge():
    """Test the Benaloh challenge endpoint with correct and incorrect candidate names."""
    
    # Load the sample encrypted ballot with nonce from create_encrypted_ballot_response.json
    try:
        with open('create_encrypted_ballot_response.json', 'r') as f:
            ballot_response = json.load(f)
    except FileNotFoundError:
        print("❌ Error: create_encrypted_ballot_response.json not found.")
        print("Please run the create_encrypted_ballot endpoint first to generate sample data.")
        return False
        
    # Extract the encrypted ballot with nonce
    encrypted_ballot_with_nonce = ballot_response.get('encrypted_ballot_with_nonce')
    if not encrypted_ballot_with_nonce:
        print("❌ Error: No encrypted_ballot_with_nonce found in response file.")
        return False
    
    # Load the original request parameters from the request file
    try:
        with open('io/create_encrypted_ballot_request.json', 'r') as f:
            original_request = json.load(f)
    except FileNotFoundError:
        print("❌ Error: create_encrypted_ballot_request.json not found.")
        return False
    
    # Test 1: Correct candidate name (should return match = true)
    print("🔍 Test 1: Testing with CORRECT candidate name...")
    print(f"Expected candidate from original request: {original_request['candidate_name']}")
    
    benaloh_request_correct = {
        "encrypted_ballot_with_nonce": encrypted_ballot_with_nonce,
        "party_names": original_request["party_names"],
        "candidate_names": original_request["candidate_names"], 
        "candidate_name": original_request["candidate_name"],  # Correct candidate
        "joint_public_key": original_request["joint_public_key"],
        "commitment_hash": original_request["commitment_hash"],
        "number_of_guardians": original_request["number_of_guardians"],
        "quorum": original_request["quorum"]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/benaloh_challenge", json=benaloh_request_correct)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Status: {result['status']}")
            print(f"✅ Match: {result['match']}")
            print(f"✅ Message: {result['message']}")
            print(f"Ballot ID: {result.get('ballot_id', 'N/A')}")
            
            if result['match']:
                print("🎉 SUCCESS: Benaloh challenge correctly verified the ballot!")
            else:
                print("❌ UNEXPECTED: Expected match=true but got match=false")
                
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False
    
    print("\n" + "="*60 + "\n")
    
    # Test 2: Incorrect candidate name (should return match = false)
    print("🔍 Test 2: Testing with INCORRECT candidate name...")
    
    # Find a different candidate name
    incorrect_candidate = None
    for candidate in original_request["candidate_names"]:
        if candidate != original_request["candidate_name"]:
            incorrect_candidate = candidate
            break
    
    if not incorrect_candidate:
        print("❌ Error: Could not find alternative candidate for testing.")
        return False
        
    print(f"Using incorrect candidate: {incorrect_candidate}")
    
    benaloh_request_incorrect = {
        "encrypted_ballot_with_nonce": encrypted_ballot_with_nonce,
        "party_names": original_request["party_names"],
        "candidate_names": original_request["candidate_names"],
        "candidate_name": incorrect_candidate,  # Wrong candidate
        "joint_public_key": original_request["joint_public_key"],
        "commitment_hash": original_request["commitment_hash"],
        "number_of_guardians": original_request["number_of_guardians"],
        "quorum": original_request["quorum"]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/benaloh_challenge", json=benaloh_request_incorrect)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Status: {result['status']}")
            print(f"✅ Match: {result['match']}")
            print(f"✅ Message: {result['message']}")
            print(f"Expected candidate: {result.get('expected_candidate', 'N/A')}")
            
            if not result['match']:
                print("🎉 SUCCESS: Benaloh challenge correctly detected the mismatch!")
            else:
                print("❌ UNEXPECTED: Expected match=false but got match=true")
                
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False
    
    return True

def test_benaloh_challenge_with_missing_fields():
    """Test error handling with missing fields."""
    print("\n" + "="*60)
    print("🔍 Test 3: Testing error handling with missing required fields...")
    
    incomplete_request = {
        "encrypted_ballot_with_nonce": "test",
        "party_names": ["Party A"],
        # Missing other required fields
    }
    
    try:
        response = requests.post(f"{BASE_URL}/benaloh_challenge", json=incomplete_request)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 400:
            result = response.json()
            print(f"✅ Status: {result['status']}")
            print(f"✅ Error message: {result['message']}")
            print("🎉 SUCCESS: API correctly handled missing fields!")
        else:
            print(f"❌ Expected 400 status code, got {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting Benaloh Challenge Tests...")
    print("="*60)
    
    # Check if server is running
    try:
        health_response = requests.get(f"{BASE_URL}/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ API server is running")
        else:
            print("❌ API server responded with error")
            sys.exit(1)
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to API server. Please ensure it's running on http://localhost:5000")
        sys.exit(1)
    
    # Run the main tests
    success = test_benaloh_challenge()
    
    # Test error handling
    test_benaloh_challenge_with_missing_fields()
    
    if success:
        print("\n🎉 All Benaloh challenge tests completed successfully!")
    else:
        print("\n❌ Some tests failed. Check the output above.")
        sys.exit(1)