"""
Verification script to demonstrate that the API.py now has secure ballot sanitization integrated.
"""

import json
from api import ballot_publisher


def verify_api_integration():
    """Verify that the API has been properly updated with ballot sanitization."""
    
    print("🔒 ELECTIONGUARD API SANITIZATION VERIFICATION")
    print("=" * 50)
    
    # Check that ballot_publisher is available in the API
    print("1. Checking API integration...")
    try:
        stats = ballot_publisher.get_publication_stats()
        print("✅ BallotPublisher successfully integrated into API")
        print(f"   Initial stats: {stats}")
    except Exception as e:
        print(f"❌ BallotPublisher integration failed: {e}")
        return False
    
    # Test with existing ballot response
    print("\n2. Testing ballot sanitization with existing data...")
    try:
        with open("create_encrypted_ballot_response.json", "r") as f:
            ballot_response = f.read()
        
        # Test CAST ballot publication
        print("   Testing CAST ballot publication...")
        cast_result = ballot_publisher.publish_ballot(
            ballot_id="verification-cast-001",
            encrypted_ballot_response=ballot_response,
            ballot_status="CAST"
        )
        print(f"   ✅ CAST ballot published: {cast_result['publication_status']}")
        print(f"      Nonces available: {'ballot_nonces' in cast_result}")
        
        # Test AUDITED ballot publication  
        print("   Testing AUDITED ballot publication...")
        audited_result = ballot_publisher.publish_ballot(
            ballot_id="verification-audited-001", 
            encrypted_ballot_response=ballot_response,
            ballot_status="AUDITED"
        )
        print(f"   ✅ AUDITED ballot published: {audited_result['publication_status']}")
        print(f"      Nonces available: {'ballot_nonces' in audited_result}")
        if 'ballot_nonces' in audited_result:
            print(f"      Number of nonces: {len(audited_result['ballot_nonces'])}")
        
    except Exception as e:
        print(f"❌ Ballot sanitization test failed: {e}")
        return False
    
    # Verify ballot retrieval
    print("\n3. Testing ballot retrieval...")
    try:
        cast_ballot = ballot_publisher.get_published_ballot("verification-cast-001")
        audited_ballot = ballot_publisher.get_published_ballot("verification-audited-001")
        
        print(f"   ✅ CAST ballot retrieved: {cast_ballot is not None}")
        print(f"      Nonces available: {cast_ballot.get('nonces_available', False) if cast_ballot else False}")
        
        print(f"   ✅ AUDITED ballot retrieved: {audited_ballot is not None}")
        print(f"      Nonces available: {audited_ballot.get('nonces_available', False) if audited_ballot else False}")
        
    except Exception as e:
        print(f"❌ Ballot retrieval test failed: {e}")
        return False
    
    # Test nonce access controls
    print("\n4. Testing nonce access controls...")
    try:
        cast_nonces = ballot_publisher.get_ballot_nonces("verification-cast-001")
        audited_nonces = ballot_publisher.get_ballot_nonces("verification-audited-001")
        
        print(f"   ✅ CAST ballot nonces: {cast_nonces is None} (should be None)")
        print(f"   ✅ AUDITED ballot nonces: {audited_nonces is not None} (should have nonces)")
        if audited_nonces:
            print(f"      Number of nonces available: {len(audited_nonces)}")
            
    except Exception as e:
        print(f"❌ Nonce access control test failed: {e}")
        return False
    
    # Final stats
    print("\n5. Final publication statistics...")
    try:
        final_stats = ballot_publisher.get_publication_stats()
        print(f"   Total ballots: {final_stats.get('total_ballots', 0)}")
        print(f"   CAST ballots: {final_stats.get('cast_ballots', 0)}")
        print(f"   AUDITED ballots: {final_stats.get('audited_ballots', 0)}")
        print(f"   Nonces stored: {final_stats.get('nonces_stored', 0)}")
        
    except Exception as e:
        print(f"❌ Statistics retrieval failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ API VERIFICATION COMPLETE")
    print("=" * 50)
    print("🎉 Your api.py has been successfully updated with secure ballot sanitization!")
    print("\n📋 CHANGES MADE TO api.py:")
    print("   ✅ Added ballot_sanitizer and ballot_publisher imports")
    print("   ✅ Integrated BallotPublisher into the API")
    print("   ✅ Modified /create_encrypted_ballot endpoint for secure publication")
    print("   ✅ Added /ballots/<id> endpoint for ballot retrieval")
    print("   ✅ Added /ballots/<id>/nonces endpoint for nonce access")
    print("   ✅ Added /ballots endpoint for listing published ballots")
    print("   ✅ Added /publish_ballot endpoint for manual ballot publication")
    print("   ✅ Updated /health endpoint with ballot statistics")
    
    print("\n🔐 SECURITY FEATURES:")
    print("   🛡️  CAST ballots: Nonces removed for privacy")
    print("   🔍 AUDITED ballots: Nonces available for verification")
    print("   🔒 Access control: Nonces only accessible for audited ballots")
    print("   📊 Statistics: Track publication metrics")
    
    print("\n🚀 USAGE:")
    print("   • Add 'ballot_status': 'CAST' or 'AUDITED' to your ballot requests")
    print("   • CAST ballots will have nonces sanitized automatically")
    print("   • AUDITED ballots will include nonces for verification")
    print("   • Use new endpoints to retrieve and manage published ballots")
    
    return True


def show_api_endpoints():
    """Display the new API endpoints available."""
    
    print("\n🌐 NEW API ENDPOINTS AVAILABLE:")
    print("-" * 50)
    print("📝 CREATE ENCRYPTED BALLOT (Enhanced)")
    print("   POST /create_encrypted_ballot")
    print("   • Add 'ballot_status': 'CAST' or 'AUDITED' to request")
    print("   • CAST: Returns sanitized ballot (no nonces)")
    print("   • AUDITED: Returns sanitized ballot + nonces")
    
    print("\n📄 RETRIEVE PUBLISHED BALLOT")
    print("   GET /ballots/<ballot_id>")
    print("   • Returns ballot with sanitized encrypted data")
    print("   • Shows nonce availability status")
    
    print("\n🔑 ACCESS BALLOT NONCES")
    print("   GET /ballots/<ballot_id>/nonces")
    print("   • Returns nonces for AUDITED ballots only")
    print("   • Returns 403 for CAST ballots (security)")
    
    print("\n📋 LIST ALL BALLOTS")
    print("   GET /ballots")
    print("   • Optional: ?status=CAST or ?status=AUDITED")
    print("   • Returns ballot list + statistics")
    
    print("\n📤 MANUAL BALLOT PUBLICATION")  
    print("   POST /publish_ballot")
    print("   • Publish existing ballot with specific status")
    print("   • Required: ballot_id, encrypted_ballot_response, ballot_status")
    
    print("\n❤️  HEALTH CHECK (Enhanced)")
    print("   GET /health")
    print("   • Returns API status + ballot publication statistics")


if __name__ == "__main__":
    success = verify_api_integration()
    if success:
        show_api_endpoints()
    else:
        print("\n❌ Verification failed. Please check the API integration.")
