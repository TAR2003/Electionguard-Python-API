"""
Service for creating encrypted tally from ballots.
"""

#!/usr/bin/env python

from flask import Flask, request, jsonify
from typing import Dict, List, Optional, Tuple, Any
import random
from datetime import datetime
import uuid
from collections import defaultdict
import hashlib
import json
from electionguard.ballot import (
    BallotBoxState,
    CiphertextBallot,
    PlaintextBallot,
    PlaintextBallotSelection,
    PlaintextBallotContest,
    SubmittedBallot,
)
from electionguard.serialize import to_raw, from_raw
from binary_serialize import to_binary_transport, from_binary_transport, from_binary_transport_to_dict
import time
from electionguard.constants import get_constants
from electionguard.data_store import DataStore
from electionguard.decryption_mediator import DecryptionMediator
from electionguard.election import CiphertextElectionContext
from electionguard.election_polynomial import (
    LagrangeCoefficientsRecord,
    ElectionPolynomial
)
from electionguard.encrypt import EncryptionDevice, EncryptionMediator
from electionguard.guardian import Guardian
from electionguard.key_ceremony_mediator import KeyCeremonyMediator
from electionguard.key_ceremony import ElectionKeyPair, ElectionPublicKey
from electionguard.ballot_box import BallotBox, get_ballots, submit_ballot
from electionguard.elgamal import ElGamalPublicKey, ElGamalSecretKey, ElGamalCiphertext
from electionguard.group import ElementModQ, ElementModP, g_pow_p, int_to_p, int_to_q
from electionguard.manifest import (
    Manifest,
    InternalManifest,
    GeopoliticalUnit,
    Party,
    Candidate,
    ContestDescription as Contest,
    SelectionDescription,
    BallotStyle,
    ElectionType,
    VoteVariationType,
    SpecVersion,
    ContactInformation,
    ReportingUnitType
)
from electionguard_tools.helpers.election_builder import ElectionBuilder
from electionguard.tally import (
    tally_ballots,
    CiphertextTally,
    PlaintextTally,
    CiphertextTallyContest,
    CiphertextTallySelection
)
from electionguard.type import BallotId, GuardianId
from electionguard.utils import get_optional
from electionguard.election_polynomial import ElectionPolynomial, Coefficient, SecretCoefficient, PublicCommitment
from electionguard.schnorr import SchnorrProof
from electionguard.elgamal import ElGamalKeyPair, ElGamalPublicKey, ElGamalSecretKey
from electionguard.hash import hash_elems
from electionguard.decryption_share import DecryptionShare, CompensatedDecryptionShare
from electionguard.decryption import (
    compute_decryption_share, 
    compute_decryption_share_for_ballot,
    compute_compensated_decryption_share,
    compute_compensated_decryption_share_for_ballot,
    decrypt_backup,
    compute_lagrange_coefficients_for_guardians as compute_lagrange_coeffs
)
from manifest_cache import get_manifest_cache



def ciphertext_tally_to_raw(tally: CiphertextTally) -> Dict:
    """Convert a CiphertextTally to a raw dictionary (plain dict, API handles serialization)."""
    return {
        "_encryption": json.loads(to_raw(tally._encryption)),
        "cast_ballot_ids": list(tally.cast_ballot_ids),
        "spoiled_ballot_ids": list(tally.spoiled_ballot_ids),
        "contests": {contest_id: json.loads(to_raw(contest)) for contest_id, contest in tally.contests.items()},
        "_internal_manifest": json.loads(to_raw(tally._internal_manifest)),
        "_manifest": json.loads(to_raw(tally._internal_manifest.manifest))
    }


def raw_to_ciphertext_tally(raw: Dict, manifest: Manifest = None) -> CiphertextTally:
    """Reconstruct a CiphertextTally from its raw dictionary (plain dict format)."""
    internal_manifest = InternalManifest(manifest)
    
    tally = CiphertextTally(
        object_id=raw.get("object_id", ""),
        _internal_manifest=internal_manifest,
        _encryption=from_raw(CiphertextElectionContext, json.dumps(raw["_encryption"])),
    )
    
    tally.cast_ballot_ids = set(raw["cast_ballot_ids"])
    tally.spoiled_ballot_ids = set(raw["spoiled_ballot_ids"])
    
    tally.contests = {
        contest_id: from_raw(CiphertextTallyContest, json.dumps(contest_raw))
        for contest_id, contest_raw in raw["contests"].items()
    }
    
    return tally


def create_encrypted_tally_service(
    party_names: List[str],
    candidate_names: List[str],
    joint_public_key: str,
    commitment_hash: str,
    encrypted_ballots: List[Dict],
    number_of_guardians: int,
    quorum: int,
    create_election_manifest_func,
    ciphertext_tally_to_raw_func
) -> Dict[str, Any]:
    """
    Service function to tally encrypted ballots.
    
    Args:
        party_names: List of party names
        candidate_names: List of candidate names
        joint_public_key: Joint public key as string
        commitment_hash: Commitment hash as string
        encrypted_ballots: List of encrypted ballot dictionaries
        number_of_guardians: Number of guardians
        quorum: Quorum for the election
        create_election_manifest_func: Function to create election manifest
        ciphertext_tally_to_raw_func: Function to serialize ciphertext tally
        
    Returns:
        Dictionary containing the tally results
        
    Raises:
        ValueError: If no ballots provided or tally fails
    """
    if not encrypted_ballots:
        raise ValueError('No ballots to tally. Provide encrypted ballots.')
    
    # Convert string inputs to integers for internal processing
    joint_public_key_int = int(joint_public_key)
    commitment_hash_int = int(commitment_hash)
    
    ciphertext_tally_json, submitted_ballots_json = tally_encrypted_ballots(
        party_names,
        candidate_names,
        joint_public_key_int,
        commitment_hash_int,
        encrypted_ballots,
        number_of_guardians,
        quorum,
        create_election_manifest_func,
        ciphertext_tally_to_raw_func
    )
    
    return {
        'ciphertext_tally': ciphertext_tally_json,
        'submitted_ballots': submitted_ballots_json
    }


def tally_encrypted_ballots(
    party_names: List[str],
    candidate_names: List[str],
    joint_public_key_json: int,
    commitment_hash_json: int,
    encrypted_ballots_json: List[Dict],
    number_of_guardians: int,
    quorum: int,
    create_election_manifest_func,
    ciphertext_tally_to_raw_func
) -> Tuple[Dict, List[Dict]]:
    """
    Tally encrypted ballots.
    
    Args:
        party_names: List of party names
        candidate_names: List of candidate names
        joint_public_key_json: Joint public key as integer
        commitment_hash_json: Commitment hash as integer
        encrypted_ballots_json: List of encrypted ballot dictionaries
        number_of_guardians: Number of guardians
        quorum: Quorum for the election
        create_election_manifest_func: Function to create election manifest
        ciphertext_tally_to_raw_func: Function to serialize ciphertext tally
        
    Returns:
        Tuple of (tally_json, submitted_ballots_json)
    """
    print(f"  \ud83d\udd0d SERVICE: create_encrypted_tally_service started")
    
    # Deserialize ballots
    deserialize_start = time.time()
    joint_public_key = int_to_p(joint_public_key_json)
    commitment_hash = int_to_q(commitment_hash_json)
    encrypted_ballots: List[CiphertextBallot] = []
    for encrypted_ballot_json in encrypted_ballots_json:
        # Binary deserialization (base64)
        encrypted_ballots.append(from_binary_transport(CiphertextBallot, encrypted_ballot_json))
    deserialize_elapsed = time.time() - deserialize_start
    print(f"    \u23f1\ufe0f  Ballot deserialization: {deserialize_elapsed*1000:.2f}ms")
    
    # Build context (use cache to avoid expensive recreation)
    context_start = time.time()
    cache = get_manifest_cache()
    internal_manifest, context = cache.get_or_create_context(
        party_names, candidate_names,
        joint_public_key_json, commitment_hash_json,
        number_of_guardians, quorum,
        create_election_manifest_func
    )
    context_elapsed = time.time() - context_start
    print(f"    \u23f1\ufe0f  Context building: {context_elapsed*1000:.2f}ms")
    
    # Submit ballots - cast all ballots (skip proof re-validation: ballots were just created by this API)
    cast_start = time.time()
    ballot_store = DataStore()
    
    submitted_ballots = []
    for ballot in encrypted_ballots:
        # Use submit_ballot directly to bypass expensive proof re-verification
        # (ballots just came from create_encrypted_ballot, already proved valid)
        submitted = submit_ballot(ballot, BallotBoxState.CAST)
        ballot_store.set(submitted.object_id, submitted)
        submitted_ballots.append(submitted)
    cast_elapsed = time.time() - cast_start
    print(f"    \u23f1\ufe0f  Ballot casting (no re-validation): {cast_elapsed*1000:.2f}ms")
    
    # Tally the ballots — use should_validate=False to skip proof re-verification
    tally_start = time.time()
    tally = CiphertextTally("election-results", internal_manifest, context)
    tally.batch_append(ballot_store, should_validate=False)
    ciphertext_tally = tally
    tally_elapsed = time.time() - tally_start
    print(f"    \u23f1\ufe0f  Tally computation: {tally_elapsed*1000:.2f}ms")
    
    # Convert to plain dicts (API layer will handle binary serialization)
    serialize_start = time.time()
    ciphertext_tally_json = ciphertext_tally_to_raw_func(ciphertext_tally)
    # Return plain dicts, not JSON strings (msgpack handles dicts natively)
    submitted_ballots_json = [json.loads(to_raw(submitted_ballot)) for submitted_ballot in submitted_ballots]
    serialize_elapsed = time.time() - serialize_start
    print(f"    ⏱️  Result conversion: {serialize_elapsed*1000:.2f}ms")
    
    total_service_time = deserialize_elapsed + context_elapsed + cast_elapsed + tally_elapsed + serialize_elapsed
    print(f"  \u2705 SERVICE COMPLETE: {total_service_time*1000:.2f}ms total")
    
    return ciphertext_tally_json, submitted_ballots_json
