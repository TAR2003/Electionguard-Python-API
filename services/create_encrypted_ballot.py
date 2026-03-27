"""
Service for creating encrypted ballots.
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
from binary_serialize import to_binary_transport, from_binary_transport
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
from electionguard.ballot_box import BallotBox, get_ballots
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



def create_election_manifest(
    party_names: List[str], 
    candidate_names: List[str],
    max_choices: int = 1
) -> Manifest:
    """Create a complete election manifest programmatically.
    
    Args:
        party_names: List of party names
        candidate_names: List of candidate names
        max_choices: Maximum number of candidates a voter can select (default 1)
    """
    # Ensure max_choices is valid
    max_choices = max(1, min(int(max_choices), len(candidate_names)))
    
    # Create geopolitical unit
    geopolitical_unit = GeopoliticalUnit(
        object_id="county-1",
        name="County 1",
        type=ReportingUnitType.county,
        contact_information=None,
    )

    # Create ballot style
    ballot_style = BallotStyle(
        object_id="ballot-style-1",
        geopolitical_unit_ids=["county-1"],
        party_ids=None,
        image_uri=None,
    )
    
    parties: List[Party] = []
    for i in range(len(party_names)):
        parties.append(
            Party(
                object_id=f"party-{i+1}",
                name=party_names[i],
                abbreviation=party_names[i],
                color=None,
                logo_uri=None,
            )
        )

    candidates: List[Candidate] = []
    for i in range(len(candidate_names)):
        candidates.append(
            Candidate(
                object_id=f"candidate-{i+1}",
                name=candidate_names[i],
                party_id=f"party-{i+1}",
            )
        )
   
    ballot_selections: List[SelectionDescription] = []
    for i in range(len(candidate_names)):
        ballot_selections.append(
            SelectionDescription(
                object_id=f"{candidate_names[i]}",
                candidate_id=f"{candidate_names[i]}",
                sequence_order=i,
            )
        )

    # Use n_of_m for multiple choices, one_of_m for single choice
    vote_variation = VoteVariationType.n_of_m if max_choices > 1 else VoteVariationType.one_of_m

    contests: List[Contest] = [
        Contest(
            object_id="contest-1",
            sequence_order=0,
            electoral_district_id="county-1",
            vote_variation=vote_variation,
            name="County Executive",
            ballot_selections=ballot_selections,
            ballot_title=None,
            ballot_subtitle=None,
            votes_allowed=max_choices,
            number_elected=max_choices,
        ),
    ]
    
    start_date = datetime(2025,1,1)
    end_date = datetime(2025,1,1)
    
    manifest = Manifest(
        election_scope_id=f"election-1",
        spec_version="1.0",
        type=ElectionType.general,
        start_date=start_date,
        end_date=end_date,
        geopolitical_units=[geopolitical_unit],
        parties=parties,
        candidates=candidates,
        contests=contests,
        ballot_styles=[ballot_style],
        name="Test Election",
        contact_information=None,
    )
    
    return manifest


def create_plaintext_ballot(party_names, candidate_names, candidate_names_to_vote, ballot_id: str, max_choices: int = 1) -> PlaintextBallot:
    """Create a single plaintext ballot for one or more selected candidates.
    
    Args:
        party_names: List of party names
        candidate_names: List of all candidate names in the election
        candidate_names_to_vote: Single candidate name (str) or list of candidate names to vote for
        ballot_id: Unique identifier for the ballot
        max_choices: Maximum allowed selections (used to recreate manifest consistently)
    """
    # Normalize to a list
    if isinstance(candidate_names_to_vote, str):
        selections_to_vote = [candidate_names_to_vote]
    else:
        selections_to_vote = list(candidate_names_to_vote)
    
    # Validate no duplicates
    if len(selections_to_vote) != len(set(selections_to_vote)):
        raise ValueError("Duplicate candidate selections are not allowed")
    
    # Validate all candidates exist
    for name in selections_to_vote:
        if name not in candidate_names:
            raise ValueError(f"Candidate '{name}' not found in election candidates")
    
    # Validate number of selections
    if len(selections_to_vote) > max_choices:
        raise ValueError(f"Too many candidates selected ({len(selections_to_vote)}). Maximum allowed is {max_choices}")
    
    manifest = create_election_manifest(party_names, candidate_names, max_choices)
    
    # Get ballot style
    ballot_style = manifest.ballot_styles[0]
    
    ballot_contests = []
    for contest in manifest.contests:
        selections = []
        for option in contest.ballot_selections:
            vote = 1 if option.object_id in selections_to_vote else 0
            selections.append(
                PlaintextBallotSelection(
                    object_id=option.object_id,
                    vote=vote,
                    is_placeholder_selection=False,
                )
            )
        ballot_contests.append(
            PlaintextBallotContest(
                object_id=contest.object_id,
                ballot_selections=selections
            )
        )
    
    return PlaintextBallot(
        object_id=ballot_id,
        style_id=ballot_style.object_id,
        contests=ballot_contests,
    )


def create_encrypted_ballot_service(
    party_names: List[str],
    candidate_names: List[str],
    candidate_names_to_vote,
    ballot_id: str,
    joint_public_key: str,
    commitment_hash: str,
    number_of_guardians: int,
    quorum: int,
    create_plaintext_ballot_func,
    create_election_manifest_func,
    generate_ballot_hash_func,
    max_choices: int = 1
) -> Dict[str, Any]:
    """
    Service function to create and encrypt a ballot.
    
    Args:
        party_names: List of party names
        candidate_names: List of all candidate names in the election
        candidate_names_to_vote: Single candidate name or list of candidate names to vote for
        ballot_id: Unique identifier for the ballot
        joint_public_key: Joint public key as string
        commitment_hash: Commitment hash as string
        number_of_guardians: Number of guardians
        quorum: Quorum for the election
        create_plaintext_ballot_func: Function to create plaintext ballot
        create_election_manifest_func: Function to create election manifest
        generate_ballot_hash_func: Function to generate ballot hash
        max_choices: Maximum number of candidates voter can select (default 1)
        
    Returns:
        Dictionary containing the encrypted ballot and hash
        
    Raises:
        ValueError: If ballot encryption fails
    """
    # Convert string inputs to integers for internal processing
    joint_public_key_int = int(joint_public_key)
    commitment_hash_int = int(commitment_hash)
    
    # Create plaintext ballot
    ballot = create_plaintext_ballot_func(party_names, candidate_names, candidate_names_to_vote, ballot_id, max_choices)
    
    # Encrypt the ballot
    encrypted_ballot = encrypt_ballot(
        party_names, 
        candidate_names, 
        joint_public_key_int,
        commitment_hash_int,
        ballot,
        number_of_guardians,
        quorum,
        create_election_manifest_func,
        max_choices
    )
    
    if not encrypted_ballot:
        raise ValueError('Failed to encrypt ballot')
    
    # Generate ballot hash
    ballot_hash = generate_ballot_hash_func(encrypted_ballot)
    
    # Serialize the ballot for response using binary serialization (FAST)
    serialized_ballot = to_binary_transport(encrypted_ballot)
    
    return {
        'encrypted_ballot': serialized_ballot,
        'ballot_hash': ballot_hash
    }


def encrypt_ballot(
    party_names: List[str],
    candidate_names: List[str],
    joint_public_key_json: int,
    commitment_hash_json: int,
    plaintext_ballot: PlaintextBallot,
    number_of_guardians: int,
    quorum: int,
    create_election_manifest_func,
    max_choices: int = 1
) -> Optional[CiphertextBallot]:
    """
    Encrypt a single ballot.
    
    Args:
        party_names: List of party names
        candidate_names: List of candidate names
        joint_public_key_json: Joint public key as integer
        commitment_hash_json: Commitment hash as integer
        plaintext_ballot: The plaintext ballot to encrypt
        number_of_guardians: Number of guardians
        quorum: Quorum for the election
        create_election_manifest_func: Function to create election manifest
        max_choices: Maximum number of candidates voter can select (default 1)
        
    Returns:
        Encrypted ballot or None if encryption fails
    """
    # Use cache to avoid expensive manifest/context recreation (critical for 50+ ballots!)
    cache = get_manifest_cache()
    internal_manifest, context = cache.get_or_create_context(
        party_names, candidate_names,
        joint_public_key_json, commitment_hash_json,
        number_of_guardians, quorum,
        create_election_manifest_func,
        max_choices
    )
    
    # Create encryption device and mediator
    device = EncryptionDevice(device_id=1, session_id=1, launch_code=1, location="polling-place")
    encrypter = EncryptionMediator(internal_manifest, context, device)
    
    # Encrypt the ballot
    encrypted_ballot = encrypter.encrypt(plaintext_ballot)
    if encrypted_ballot:
        return get_optional(encrypted_ballot)
    return None
