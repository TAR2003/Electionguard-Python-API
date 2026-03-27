#!/usr/bin/env python

from typing import Dict, Any, List, Set
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
    candidate_names_to_verify,
    joint_public_key: str,
    commitment_hash: str,
    number_of_guardians: int,
    quorum: int
) -> Dict[str, Any]:
    """
    Perform Benaloh challenge by decrypting an encrypted ballot with nonces
    and verifying if the choices match the expected candidates.
    
    Args:
        encrypted_ballot_with_nonce: JSON string of encrypted ballot containing nonces
        party_names: List of party names
        candidate_names: List of all candidate names in the election
        candidate_names_to_verify: Single candidate name (str) or list of candidate names to verify against
        joint_public_key: Joint public key used for encryption
        commitment_hash: Commitment hash
        number_of_guardians: Number of guardians
        quorum: Quorum threshold
        
    Returns:
        Dict containing verification result and details
    """
    try:
        # Normalize candidate_names_to_verify to a set
        if isinstance(candidate_names_to_verify, str):
            expected_candidates: Set[str] = {candidate_names_to_verify}
        else:
            expected_candidates: Set[str] = set(candidate_names_to_verify)

        # Decode the binary-transport (base64 msgpack) ballot back to a dict.
        # The Java backend stores encrypted_ballot_with_nonce as the base64 binary
        # transport string produced by to_binary_transport(); json.loads() fails on it.
        ballot_data = from_binary_transport_to_dict(encrypted_ballot_with_nonce)
        
        # Convert joint public key string to ElGamalPublicKey
        joint_public_key_element = int_to_p(int(joint_public_key))
        public_key = ElGamalPublicKey(joint_public_key_element)
        
        # Decrypt each selection using its nonce and find which candidates were chosen
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
                    from electionguard.elgamal import ElGamalCiphertext
                    
                    elgamal_ciphertext = ElGamalCiphertext(pad, data)
                    
                    # Decrypt with known nonce
                    decrypted_value = elgamal_ciphertext.decrypt_known_nonce(public_key, nonce)
                    
                    decrypted_votes[selection_id] = decrypted_value
                    print(f"Decrypted {selection_id}: {decrypted_value}")
        
        # Collect all candidates that received a vote (value == 1)
        voted_candidates: Set[str] = set()
        for candidate, vote_count in decrypted_votes.items():
            if vote_count == 1:
                voted_candidates.add(candidate)
        
        print(f"Voted candidates: {voted_candidates}")
        print(f"Expected candidates: {expected_candidates}")
        
        # Check if the voted candidates exactly match the expected candidates
        if voted_candidates == expected_candidates:
            return {
                "success": True,
                "match": True,
                "message": f"Ballot choice matches expected selection: {', '.join(sorted(expected_candidates))}",
                "ballot_id": ballot_data.get("object_id"),
                "verified_candidates": sorted(voted_candidates),
                "verified_candidate": ', '.join(sorted(voted_candidates)),
                "decrypted_votes": decrypted_votes
            }
        else:
            return {
                "success": True,
                "match": False,
                "message": (
                    f"Ballot choice does NOT match expected selection. "
                    f"Expected: {', '.join(sorted(expected_candidates))}. "
                    f"Actual: {', '.join(sorted(voted_candidates)) if voted_candidates else 'none'}"
                ),
                "ballot_id": ballot_data.get("object_id"),
                "expected_candidates": sorted(expected_candidates),
                "expected_candidate": ', '.join(sorted(expected_candidates)),
                "actual_candidates": sorted(voted_candidates),
                "verified_candidate": ', '.join(sorted(voted_candidates)) if voted_candidates else None,
                "decrypted_votes": decrypted_votes
            }
            
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": f"Benaloh challenge failed: {str(e)}",
            "traceback": traceback.format_exc()
        }
