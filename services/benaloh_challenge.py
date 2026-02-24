#!/usr/bin/env python

from typing import Dict, Any, List
import json
from electionguard.serialize import from_raw, to_raw
from electionguard.ballot import CiphertextBallot, PlaintextBallot
from electionguard.manifest import Manifest
from electionguard.election import CiphertextElectionContext, make_ciphertext_election_context
from electionguard.group import ElementModP, ElementModQ, int_to_q, int_to_p, g_pow_p
from electionguard.elgamal import ElGamalPublicKey
from binary_serialize import from_binary_transport_to_dict
def benaloh_challenge_service(
    encrypted_ballot_with_nonce: str,
    party_names: List[str],
    candidate_names: List[str], 
    candidate_name: str,
    joint_public_key: str,
    commitment_hash: str,
    number_of_guardians: int,
    quorum: int
) -> Dict[str, Any]:
    """
    Perform Benaloh challenge by decrypting an encrypted ballot with nonces
    and verifying if the choice matches the expected candidate.
    
    Args:
        encrypted_ballot_with_nonce: JSON string of encrypted ballot containing nonces
        party_names: List of party names
        candidate_names: List of candidate names
        candidate_name: Expected candidate choice to verify against
        joint_public_key: Joint public key used for encryption
        commitment_hash: Commitment hash
        number_of_guardians: Number of guardians
        quorum: Quorum threshold
        
    Returns:
        Dict containing verification result and details
    """
    try:
        # Decode the binary-transport (base64 msgpack) ballot back to a dict.
        # The Java backend stores encrypted_ballot_with_nonce as the base64 binary
        # transport string produced by to_binary_transport(); json.loads() fails on it.
        ballot_data = from_binary_transport_to_dict(encrypted_ballot_with_nonce)
        
        # Convert joint public key string to ElGamalPublicKey
        joint_public_key_element = int_to_p(int(joint_public_key))
        public_key = ElGamalPublicKey(joint_public_key_element)
        
        # Decrypt each selection using its nonce and find which candidate was chosen
        decrypted_votes = {}
        
        # Process each contest
        for contest in ballot_data["contests"]:
            contest_id = contest["object_id"]
            
            # Process each selection in the contest
            for selection in contest["ballot_selections"]:
                selection_id = selection["object_id"]
                selection_nonce_str = selection.get("nonce")
                
                if selection_nonce_str and not selection.get("is_placeholder_selection", False):
                    # Convert nonce from hex string to ElementModQ
                    nonce = int_to_q(int(selection_nonce_str, 16))
                    
                    # Extract ciphertext pad and data
                    ciphertext = selection["ciphertext"]
                    pad = int_to_p(int(ciphertext["pad"], 16))
                    data = int_to_p(int(ciphertext["data"], 16))
                    
                    # Decrypt using the known nonce: plaintext = data / (pad^nonce)
                    # Actually, we use decrypt_known_nonce method from ElGamal
                    from electionguard.elgamal import ElGamalCiphertext
                    
                    elgamal_ciphertext = ElGamalCiphertext(pad, data)
                    
                    # Decrypt with known nonce
                    decrypted_value = elgamal_ciphertext.decrypt_known_nonce(public_key, nonce)
                    
                    decrypted_votes[selection_id] = decrypted_value
                    print(f"Decrypted {selection_id}: {decrypted_value}")
        
        # Find which candidate received the vote (should have value 1)
        voted_candidate = None
        for candidate, vote_count in decrypted_votes.items():
            if vote_count == 1:
                voted_candidate = candidate
                break
        
        # Check if the voted candidate matches the expected candidate
        if voted_candidate == candidate_name:
            return {
                "success": True,
                "match": True,
                "message": f"Ballot choice matches expected candidate: {candidate_name}",
                "ballot_id": ballot_data.get("object_id"),
                "verified_candidate": voted_candidate,
                "decrypted_votes": decrypted_votes
            }
        else:
            return {
                "success": True, 
                "match": False,
                "message": f"Ballot choice does NOT match expected candidate: {candidate_name}. Actual choice: {voted_candidate}",
                "ballot_id": ballot_data.get("object_id"),
                "expected_candidate": candidate_name,
                "actual_candidate": voted_candidate,
                "decrypted_votes": decrypted_votes
            }
            
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": f"Benaloh challenge failed: {str(e)}",
            "traceback": traceback.format_exc()
        }
