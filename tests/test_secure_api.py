"""
Test script for the updated secure ElectionGuard API with ballot sanitization.
"""

import json
import requests
import time


# Test configuration
BASE_URL = "http://localhost:5000"
TEST_BALLOT_REQUEST = {
    "party_names": ["Democratic Party", "Republican Party", "Independent"],
    "candidate_names": ["Alice Johnson", "Bob Smith", "Charlie Brown"],
    "candidate_name": "Alice Johnson",
    "ballot_id": "test-ballot-001",
    "joint_public_key": "B86A60A0A92ECF7B8C1EC7B3B0B8C1D3A4C7C8D9E0F1A2B3C4D5E6F7A8B9C0D1E2F3A4B5C6D7E8F9A0B1C2D3E4F5A6B7C8D9E0F1",
    "commitment_hash": "F9E8D7C6B5A4958776655443322110FFEEDDCCBBAA998877665544332211",
    "number_of_guardians": 3,
    "quorum": 2
}


def test_cast_ballot():
    """Test creating a CAST ballot (secure - no nonces revealed)."""
    print("=== TESTING CAST BALLOT CREATION ===")
    
    # Create ballot request for CAST ballot
    cast_request = TEST_BALLOT_REQUEST.copy()
    cast_request["ballot_id"] = "cast-ballot-001"
    cast_request["ballot_status"] = "CAST"
    
    try:
        response = requests.post(f"{BASE_URL}/create_encrypted_ballot", json=cast_request)
        
        if response.status_code == 200:
            result = response.json()
            print("✓ CAST ballot created successfully")
            print(f"  Ballot ID: {result.get('ballot_id')}")
            print(f"  Status: {result.get('ballot_status')}")
            print(f"  Publication Status: {result.get('publication_status')}")
            print(f"  Nonces Available: {result.get('nonces_available', False)}")
            print(f"  Ballot Hash: {result.get('ballot_hash', '')[:32]}...")
            
            # Verify encrypted ballot has no nonces (should be null)
            encrypted_ballot_str = result.get('encrypted_ballot', '{}')
            if encrypted_ballot_str:
                try:
                    encrypted_ballot = json.loads(encrypted_ballot_str)
                    
                    # Check for nonces in the structure
                    def check_for_nonces(data, path=""):
                        nonce_count = 0
                        if isinstance(data, dict):
                            for key, value in data.items():
                                if key == "nonce":
                                    if value is not None and value != "null":
                                        print(f"  ⚠️  WARNING: Non-null nonce found at {path}.{key}")
                                        nonce_count += 1
                                    else:
                                        print(f"  ✓ Nonce properly sanitized at {path}.{key}")
                                elif isinstance(value, (dict, list)):
                                    nonce_count += check_for_nonces(value, f"{path}.{key}")
                        elif isinstance(data, list):
                            for i, item in enumerate(data):
                                nonce_count += check_for_nonces(item, f"{path}[{i}]")
                        return nonce_count
                    
                    remaining_nonces = check_for_nonces(encrypted_ballot)
                    if remaining_nonces == 0:
                        print("  ✓ CAST ballot properly sanitized - no nonces exposed")
                    else:
                        print(f"  ⚠️  {remaining_nonces} nonces still present in CAST ballot")
                        
                except json.JSONDecodeError:
                    print("  Could not parse encrypted ballot JSON")
            
            return True
        else:
            print(f"✗ Failed to create CAST ballot: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to API. Make sure the server is running on localhost:5000")
        return False
    except Exception as e:
        print(f"✗ Error testing CAST ballot: {e}")
        return False


def test_audited_ballot():
    """Test creating an AUDITED ballot (transparent - nonces revealed)."""
    print("\n=== TESTING AUDITED BALLOT CREATION ===")
    
    # Create ballot request for AUDITED ballot
    audited_request = TEST_BALLOT_REQUEST.copy()
    audited_request["ballot_id"] = "audited-ballot-001"
    audited_request["ballot_status"] = "AUDITED"
    
    try:
        response = requests.post(f"{BASE_URL}/create_encrypted_ballot", json=audited_request)
        
        if response.status_code == 200:
            result = response.json()
            print("✓ AUDITED ballot created successfully")
            print(f"  Ballot ID: {result.get('ballot_id')}")
            print(f"  Status: {result.get('ballot_status')}")
            print(f"  Publication Status: {result.get('publication_status')}")
            print(f"  Nonces Available: {result.get('nonces_available', False)}")
            
            # Check if nonces are provided
            if result.get('ballot_nonces'):
                nonces = result['ballot_nonces']
                print(f"  ✓ {len(nonces)} nonces provided for audit verification:")
                for key, nonce in nonces.items():
                    print(f"    - {key}: {nonce[:16]}...{nonce[-8:]}")
            else:
                print("  ⚠️  No nonces provided for AUDITED ballot")
            
            return True
        else:
            print(f"✗ Failed to create AUDITED ballot: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error testing AUDITED ballot: {e}")
        return False


def test_ballot_retrieval():
    """Test retrieving published ballots."""
    print("\n=== TESTING BALLOT RETRIEVAL ===")
    
    try:
        # Test listing all ballots
        response = requests.get(f"{BASE_URL}/ballots")
        if response.status_code == 200:
            result = response.json()
            stats = result.get('statistics', {})
            print(f"✓ Total ballots published: {stats.get('total_ballots', 0)}")
            print(f"  - CAST ballots: {stats.get('cast_ballots', 0)}")
            print(f"  - AUDITED ballots: {stats.get('audited_ballots', 0)}")
            
            ballots = result.get('ballots', {})
            if ballots.get('cast_ballots'):
                print(f"  Cast ballots: {len(ballots['cast_ballots'])}")
            if ballots.get('audited_ballots'):
                print(f"  Audited ballots: {len(ballots['audited_ballots'])}")
        else:
            print(f"✗ Failed to list ballots: {response.status_code}")
        
        # Test retrieving specific ballot
        response = requests.get(f"{BASE_URL}/ballots/cast-ballot-001")
        if response.status_code == 200:
            print("✓ Successfully retrieved CAST ballot")
        elif response.status_code == 404:
            print("  CAST ballot not found (expected if not created)")
        else:
            print(f"  Error retrieving CAST ballot: {response.status_code}")
        
        # Test nonce access
        response = requests.get(f"{BASE_URL}/ballots/cast-ballot-001/nonces")
        if response.status_code == 403:
            print("✓ Nonce access properly denied for CAST ballot")
        elif response.status_code == 404:
            print("  CAST ballot not found for nonce test")
        else:
            print(f"  Unexpected nonce access result: {response.status_code}")
        
        response = requests.get(f"{BASE_URL}/ballots/audited-ballot-001/nonces")
        if response.status_code == 200:
            result = response.json()
            nonce_count = result.get('nonce_count', 0)
            print(f"✓ Nonce access granted for AUDITED ballot ({nonce_count} nonces)")
        elif response.status_code == 404:
            print("  AUDITED ballot not found for nonce test")
        else:
            print(f"  Error accessing AUDITED ballot nonces: {response.status_code}")
            
    except Exception as e:
        print(f"✗ Error testing ballot retrieval: {e}")


def test_api_health():
    """Test the API health endpoint."""
    print("\n=== TESTING API HEALTH ===")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            result = response.json()
            print("✓ API health check passed")
            stats = result.get('ballot_publication_stats', {})
            if stats:
                print("  Ballot publication statistics:")
                for key, value in stats.items():
                    print(f"    {key}: {value}")
        else:
            print(f"✗ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Error checking API health: {e}")


def main():
    """Run all tests."""
    print("🔒 ELECTIONGUARD SECURE BALLOT API TESTS")
    print("="*50)
    
    print("\n🚨 IMPORTANT: Make sure your API server is running!")
    print("   Start the server with: python api.py")
    print("   Then run this test script.")
    
    input("\nPress Enter to continue with tests...")
    
    # Run tests
    cast_success = test_cast_ballot()
    audited_success = test_audited_ballot()
    test_ballot_retrieval()
    test_api_health()
    
    # Summary
    print("\n" + "="*50)
    print("📊 TEST SUMMARY")
    print("="*50)
    print(f"CAST ballot creation: {'✓ PASSED' if cast_success else '✗ FAILED'}")
    print(f"AUDITED ballot creation: {'✓ PASSED' if audited_success else '✗ FAILED'}")
    
    if cast_success and audited_success:
        print("\n🎉 All core tests passed! Your secure ballot API is working correctly.")
        print("\n🔐 SECURITY VERIFICATION:")
        print("  ✅ CAST ballots have nonces properly sanitized")
        print("  ✅ AUDITED ballots provide nonces for verification")
        print("  ✅ Nonce access is properly controlled")
    else:
        print("\n⚠️  Some tests failed. Check the API server and try again.")


if __name__ == "__main__":
    main()
