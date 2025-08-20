"""
Ballot Sanitization Module for ElectionGuard

This module provides functions to sanitize encrypted ballots by extracting nonces
for secure publication based on ballot status (CAST vs AUDITED).
"""

import json
import copy
from typing import Dict, Tuple, Any, Optional


def extract_nonces_from_dict(data: Dict[str, Any], nonces_dict: Dict[str, str], path: str = "") -> Dict[str, Any]:
    """
    Recursively extract nonces from a dictionary structure.
    
    Args:
        data: The dictionary to process
        nonces_dict: Dictionary to store extracted nonces
        path: Current path in the data structure for unique identification
    
    Returns:
        Dictionary with nonces set to None
    """
    if not isinstance(data, dict):
        return data
    
    result = {}
    
    for key, value in data.items():
        current_path = f"{path}.{key}" if path else key
        
        if key == "nonce" and isinstance(value, str):
            # Extract the nonce and set to None in the sanitized version
            nonces_dict[current_path] = value
            result[key] = None
        elif isinstance(value, dict):
            # Recursively process nested dictionaries
            result[key] = extract_nonces_from_dict(value, nonces_dict, current_path)
        elif isinstance(value, list):
            # Process lists that might contain dictionaries with nonces
            result[key] = []
            for idx, item in enumerate(value):
                item_path = f"{current_path}[{idx}]"
                if isinstance(item, dict):
                    result[key].append(extract_nonces_from_dict(item, nonces_dict, item_path))
                else:
                    result[key].append(item)
        else:
            # Keep other values as-is
            result[key] = value
    
    return result


def extract_selection_nonces(ballot_selections: list) -> Dict[str, str]:
    """
    Extract nonces from ballot selections using object_id as key for easier identification.
    
    Args:
        ballot_selections: List of ballot selection objects
    
    Returns:
        Dictionary mapping object_id to nonce value
    """
    selection_nonces = {}
    
    for selection in ballot_selections:
        if isinstance(selection, dict) and "object_id" in selection and "nonce" in selection:
            object_id = selection["object_id"]
            nonce = selection["nonce"]
            if nonce:  # Only add if nonce exists
                selection_nonces[object_id] = nonce
    
    return selection_nonces


def sanitize_ballot(encrypted_ballot_json: str) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """
    Sanitize an encrypted ballot by extracting all nonces into a separate structure.
    
    Args:
        encrypted_ballot_json: JSON string of the encrypted ballot
    
    Returns:
        Tuple of (sanitized_ballot_dict, extracted_nonces_dict)
    """
    try:
        # Parse the JSON string
        ballot_data = json.loads(encrypted_ballot_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")
    
    # Create a deep copy to avoid modifying the original
    sanitized_ballot = copy.deepcopy(ballot_data)
    
    # Dictionary to store all extracted nonces
    all_nonces = {}
    
    # Extract top-level ballot nonce
    if "nonce" in sanitized_ballot and sanitized_ballot["nonce"]:
        all_nonces["ballot_nonce"] = sanitized_ballot["nonce"]
        sanitized_ballot["nonce"] = None
    
    # Process contests and their ballot selections
    if "contests" in sanitized_ballot:
        for contest_idx, contest in enumerate(sanitized_ballot["contests"]):
            contest_id = contest.get("object_id", f"contest_{contest_idx}")
            
            # Extract contest-level nonce if exists
            if "nonce" in contest and contest["nonce"]:
                all_nonces[f"{contest_id}_nonce"] = contest["nonce"]
                contest["nonce"] = None
            
            # Process ballot selections
            if "ballot_selections" in contest:
                for selection in contest["ballot_selections"]:
                    if "object_id" in selection and "nonce" in selection and selection["nonce"]:
                        object_id = selection["object_id"]
                        all_nonces[object_id] = selection["nonce"]
                        selection["nonce"] = None
    
    # Use the comprehensive extraction function as a fallback to catch any remaining nonces
    remaining_nonces = {}
    sanitized_ballot = extract_nonces_from_dict(sanitized_ballot, remaining_nonces)
    
    # Merge any remaining nonces found
    all_nonces.update(remaining_nonces)
    
    return sanitized_ballot, all_nonces


def prepare_ballot_for_publication(encrypted_ballot_json: str, ballot_status: str) -> Dict[str, Any]:
    """
    Prepare an encrypted ballot for publication based on its status.
    
    Args:
        encrypted_ballot_json: JSON string of the encrypted ballot
        ballot_status: Either "CAST" or "AUDITED"
    
    Returns:
        Dictionary containing ballot_for_publication and nonces_to_reveal (if applicable)
    """
    if ballot_status.upper() not in ["CAST", "AUDITED"]:
        raise ValueError("ballot_status must be either 'CAST' or 'AUDITED'")
    
    # Sanitize the ballot and extract nonces
    sanitized_ballot, extracted_nonces = sanitize_ballot(encrypted_ballot_json)
    
    if ballot_status.upper() == "CAST":
        # For cast ballots - publish sanitized ballot, keep nonces secret
        return {
            "ballot_for_publication": sanitized_ballot,
            "nonces_to_reveal": None  # Never reveal for cast ballots
        }
    elif ballot_status.upper() == "AUDITED":
        # For audited ballots - publish both sanitized ballot and nonces
        return {
            "ballot_for_publication": sanitized_ballot,
            "nonces_to_reveal": extracted_nonces  # OK to reveal for audited ballots
        }


def process_ballot_response(ballot_response_json: str, ballot_status: str) -> Dict[str, Any]:
    """
    Process a complete ballot response (including status and ballot_hash) for publication.
    
    Args:
        ballot_response_json: JSON string of the complete ballot response
        ballot_status: Either "CAST" or "AUDITED"
    
    Returns:
        Dictionary with sanitized response ready for publication
    """
    try:
        response_data = json.loads(ballot_response_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")
    
    if "encrypted_ballot" not in response_data:
        raise ValueError("No 'encrypted_ballot' field found in response")
    
    # Process the encrypted ballot
    publication_data = prepare_ballot_for_publication(
        response_data["encrypted_ballot"], 
        ballot_status
    )
    
    # Create the final response maintaining the original structure
    result = {
        "status": response_data.get("status", "success"),
        "ballot_hash": response_data.get("ballot_hash"),
        "sanitized_encrypted_ballot": json.dumps(publication_data["ballot_for_publication"]),
        "nonces_to_reveal": publication_data["nonces_to_reveal"]
    }
    
    return result


# Example usage and testing functions
def demo_sanitization():
    """
    Demonstrate the sanitization functionality with example data.
    """
    # Example encrypted ballot JSON (simplified)
    example_ballot = {
        "object_id": "ballot-1",
        "nonce": "BALLOT_NONCE_123",
        "contests": [{
            "object_id": "contest-1",
            "ballot_selections": [
                {
                    "object_id": "Alice Johnson",
                    "nonce": "ALICE_NONCE_456",
                    "ciphertext": {"pad": "pad_data", "data": "encrypted_data"}
                },
                {
                    "object_id": "Bob Smith",
                    "nonce": "BOB_NONCE_789",
                    "ciphertext": {"pad": "pad_data", "data": "encrypted_data"}
                }
            ]
        }]
    }
    
    ballot_json = json.dumps(example_ballot)
    
    print("=== ORIGINAL BALLOT ===")
    print(json.dumps(example_ballot, indent=2))
    
    print("\n=== SANITIZED BALLOT ===")
    sanitized, nonces = sanitize_ballot(ballot_json)
    print(json.dumps(sanitized, indent=2))
    
    print("\n=== EXTRACTED NONCES ===")
    print(json.dumps(nonces, indent=2))
    
    print("\n=== CAST BALLOT PUBLICATION ===")
    cast_result = prepare_ballot_for_publication(ballot_json, "CAST")
    print(json.dumps(cast_result, indent=2))
    
    print("\n=== AUDITED BALLOT PUBLICATION ===")
    audited_result = prepare_ballot_for_publication(ballot_json, "AUDITED")
    print(json.dumps(audited_result, indent=2))


if __name__ == "__main__":
    demo_sanitization()
