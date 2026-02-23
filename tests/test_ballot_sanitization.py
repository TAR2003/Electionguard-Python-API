"""
Test script to demonstrate ballot sanitization with actual encrypted ballot data.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from ballot_sanitizer import (
    sanitize_ballot, 
    prepare_ballot_for_publication, 
    process_ballot_response
)


def test_with_actual_ballot():
    """
    Test the sanitization with the actual encrypted ballot response.
    """
    # Load the actual encrypted ballot response
    try:
        with open("create_encrypted_ballot_response.json", "r") as f:
            ballot_response = f.read()
    except FileNotFoundError:
        print("Error: create_encrypted_ballot_response.json not found")
        return
    
    print("=== TESTING WITH ACTUAL ENCRYPTED BALLOT ===\n")
    
    # Parse the response to get the encrypted ballot
    response_data = json.loads(ballot_response)
    encrypted_ballot_json = response_data["encrypted_ballot"]
    
    print("1. ORIGINAL BALLOT STRUCTURE:")
    print("-" * 50)
    # Parse and display structure (truncated for readability)
    ballot_data = json.loads(encrypted_ballot_json)
    print(f"Ballot ID: {ballot_data.get('object_id')}")
    print(f"Top-level nonce present: {'nonce' in ballot_data}")
    
    if "contests" in ballot_data:
        for i, contest in enumerate(ballot_data["contests"]):
            print(f"\nContest {i+1}: {contest.get('object_id')}")
            print(f"Contest nonce present: {'nonce' in contest}")
            
            if "ballot_selections" in contest:
                print("  Selections:")
                for selection in contest["ballot_selections"]:
                    object_id = selection.get("object_id", "Unknown")
                    has_nonce = "nonce" in selection and selection["nonce"] is not None
                    is_placeholder = selection.get("is_placeholder_selection", False)
                    print(f"    - {object_id}: nonce={has_nonce}, placeholder={is_placeholder}")
    
    print("\n" + "="*80)
    print("2. SANITIZATION RESULTS:")
    print("-" * 50)
    
    # Test sanitization
    sanitized_ballot, extracted_nonces = sanitize_ballot(encrypted_ballot_json)
    
    print(f"Number of nonces extracted: {len(extracted_nonces)}")
    print("\nExtracted nonces:")
    for key, nonce in extracted_nonces.items():
        print(f"  {key}: {nonce[:16]}...{nonce[-16:] if len(nonce) > 32 else nonce}")
    
    print("\n" + "="*80)
    print("3. CAST BALLOT PREPARATION:")
    print("-" * 50)
    
    cast_result = prepare_ballot_for_publication(encrypted_ballot_json, "CAST")
    print(f"Nonces to reveal: {cast_result['nonces_to_reveal']}")
    print("✓ Cast ballot ready - nonces hidden for security")
    
    print("\n" + "="*80)
    print("4. AUDITED BALLOT PREPARATION:")
    print("-" * 50)
    
    audited_result = prepare_ballot_for_publication(encrypted_ballot_json, "AUDITED")
    nonces_count = len(audited_result['nonces_to_reveal']) if audited_result['nonces_to_reveal'] else 0
    print(f"Nonces to reveal: {nonces_count} nonces available")
    print("✓ Audited ballot ready - nonces available for verification")
    
    print("\n" + "="*80)
    print("5. COMPLETE RESPONSE PROCESSING:")
    print("-" * 50)
    
    # Test processing the complete response
    cast_response = process_ballot_response(ballot_response, "CAST")
    audited_response = process_ballot_response(ballot_response, "AUDITED")
    
    print("Cast response structure:")
    for key in cast_response.keys():
        if key == "nonces_to_reveal":
            print(f"  {key}: {cast_response[key]}")
        else:
            print(f"  {key}: {type(cast_response[key]).__name__}")
    
    print("\nAudited response structure:")
    for key in audited_response.keys():
        if key == "nonces_to_reveal":
            nonce_count = len(audited_response[key]) if audited_response[key] else 0
            print(f"  {key}: {nonce_count} nonces")
        else:
            print(f"  {key}: {type(audited_response[key]).__name__}")
    
    # Verify sanitization worked
    print("\n" + "="*80)
    print("6. VERIFICATION:")
    print("-" * 50)
    
    # Check that sanitized ballot has no nonces
    sanitized_json = cast_response["sanitized_encrypted_ballot"]
    sanitized_data = json.loads(sanitized_json)
    
    def count_nonces_in_data(data, path=""):
        count = 0
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "nonce" and value is not None:
                    print(f"  WARNING: Non-null nonce found at {path}.{key}: {value}")
                    count += 1
                elif isinstance(value, (dict, list)):
                    count += count_nonces_in_data(value, f"{path}.{key}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                count += count_nonces_in_data(item, f"{path}[{i}]")
        return count
    
    remaining_nonces = count_nonces_in_data(sanitized_data)
    if remaining_nonces == 0:
        print("✓ Verification passed: No nonces found in sanitized ballot")
    else:
        print(f"⚠ Verification warning: {remaining_nonces} nonces still present")
    
    # Save sanitized versions for inspection
    with open("sanitized_cast_ballot.json", "w") as f:
        json.dump(cast_response, f, indent=2)
    
    with open("sanitized_audited_ballot.json", "w") as f:
        json.dump(audited_response, f, indent=2)
    
    print(f"\n✓ Sanitized ballots saved to:")
    print(f"  - sanitized_cast_ballot.json")
    print(f"  - sanitized_audited_ballot.json")


def verify_nonce_extraction():
    """
    Additional verification to ensure all nonces are properly extracted.
    """
    print("\n" + "="*80)
    print("DETAILED NONCE EXTRACTION VERIFICATION:")
    print("-" * 50)
    
    try:
        with open("create_encrypted_ballot_response.json", "r") as f:
            ballot_response = f.read()
        
        response_data = json.loads(ballot_response)
        encrypted_ballot_json = response_data["encrypted_ballot"]
        ballot_data = json.loads(encrypted_ballot_json)
        
        # Count nonces in original ballot
        def find_all_nonces(data, path="", nonces_found=None):
            if nonces_found is None:
                nonces_found = []
            
            if isinstance(data, dict):
                for key, value in data.items():
                    current_path = f"{path}.{key}" if path else key
                    if key == "nonce" and value:
                        nonces_found.append((current_path, value))
                    elif isinstance(value, (dict, list)):
                        find_all_nonces(value, current_path, nonces_found)
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    find_all_nonces(item, f"{path}[{i}]", nonces_found)
            
            return nonces_found
        
        original_nonces = find_all_nonces(ballot_data)
        print(f"Original ballot contains {len(original_nonces)} nonces:")
        
        for path, nonce in original_nonces:
            print(f"  {path}: {nonce[:16]}...{nonce[-8:]}")
        
        # Test extraction
        sanitized_ballot, extracted_nonces = sanitize_ballot(encrypted_ballot_json)
        
        print(f"\nExtracted {len(extracted_nonces)} nonces:")
        for key, nonce in extracted_nonces.items():
            print(f"  {key}: {nonce[:16]}...{nonce[-8:]}")
        
        # Verify counts match
        if len(original_nonces) == len(extracted_nonces):
            print(f"\n✓ SUCCESS: All {len(original_nonces)} nonces successfully extracted")
        else:
            print(f"\n⚠ MISMATCH: Found {len(original_nonces)} nonces but extracted {len(extracted_nonces)}")
        
    except Exception as e:
        print(f"Error during verification: {e}")


if __name__ == "__main__":
    test_with_actual_ballot()
    verify_nonce_extraction()
