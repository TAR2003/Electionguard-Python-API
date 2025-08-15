"""
Service for setting up guardians and creating joint key with complete backup key sharing.
"""

#!/usr/bin/env python

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


def setup_guardians_service(
    number_of_guardians: int,
    quorum: int,
    party_names: List[str],
    candidate_names: List[str]
) -> Dict[str, Any]:
    """
    Service function to setup guardians and create joint key with complete backup key sharing.
    
    This implements the ElectionGuard Backup Key Share Generation and Distribution Process:
    1. Each guardian generates their private key, public key, and secret polynomial
    2. Each guardian evaluates their polynomial at other guardians' identifier points
    3. Each guardian encrypts backup shares using recipients' auxiliary public keys
    4. The mediator (server) distributes encrypted shares to designated recipients
    5. Recipients decrypt and verify shares using mathematical proofs
    
    Args:
        number_of_guardians: Number of guardians to create
        quorum: Minimum number of guardians needed for decryption
        party_names: List of party names
        candidate_names: List of candidate names
        
    Returns:
        Dictionary containing the setup results with complete backup key shares
        
    Raises:
        ValueError: If quorum validation fails
    """
    print(f"\n🔹 INITIALIZING ELECTIONGUARD BACKUP KEY SHARING CEREMONY")
    print(f"   • Number of Guardians: {number_of_guardians}")
    print(f"   • Quorum Threshold: {quorum}")
    
    # Validate quorum
    if quorum > number_of_guardians:
        raise ValueError('Quorum cannot be greater than number of guardians')
    
    if quorum < 1:
        raise ValueError('Quorum must be at least 1')
    
    # PHASE 1: Setup Guardians with Private Keys, Public Keys, and Polynomials
    print(f"\n🔸 PHASE 1: Creating {number_of_guardians} guardians with cryptographic keys")
    guardians: List[Guardian] = []
    for i in range(number_of_guardians):
        guardian = Guardian.from_nonce(
            str(i + 1),  # guardian id
            i + 1,  # sequence order
            number_of_guardians,
            quorum,
        )
        guardians.append(guardian)
        print(f"   ✓ Guardian {guardian.id}: Generated private key, public key, and secret polynomial")
    
    # PHASE 2: Setup Key Ceremony Mediator (Server/Relay)
    print(f"\n🔸 PHASE 2: Setting up Key Ceremony Mediator (acts as encrypted message relay)")
    mediator = KeyCeremonyMediator(
        "key-ceremony-mediator", 
        guardians[0].ceremony_details
    )
    print(f"   ✓ Mediator ready to facilitate secure backup key distribution")
    
    # ROUND 1: Public Key Sharing and Announcement
    print(f"\n🔸 ROUND 1: Public Key Sharing and Guardian Announcement")
    for guardian in guardians:
        mediator.announce(guardian.share_key())
        print(f"   ✓ Guardian {guardian.id}: Announced presence and shared election public key")
        
    # Share Keys
    print(f"\n   📤 Distributing announced public keys to all guardians...")
    for guardian in guardians:
        announced_keys = get_optional(mediator.share_announced())
        for key in announced_keys:
            if guardian.id != key.owner_id:
                guardian.save_guardian_key(key)
        print(f"   ✓ Guardian {guardian.id}: Received and stored public keys from other guardians")
    
    # ROUND 2: Election Partial Key Backup Generation and Sharing
    print(f"\n🔸 ROUND 2: Backup Key Share Generation and Encrypted Distribution")
    for sending_guardian in guardians:
        print(f"\n   👤 Guardian {sending_guardian.id}'s Backup Generation Process:")
        
        # Generate backup shares by evaluating polynomial at other guardians' points
        print(f"      🧮 Evaluating secret polynomial P_{sending_guardian.id}(x) at other guardian points...")
        sending_guardian.generate_election_partial_key_backups()
        
        backups = []
        shares_generated = 0
        for designated_guardian in guardians:
            if designated_guardian.id != sending_guardian.id:
                # This creates P_A(ID_B) = backup share for Guardian B
                backup = get_optional(
                    sending_guardian.share_election_partial_key_backup(
                        designated_guardian.id
                    )
                )
                backups.append(backup)
                shares_generated += 1
                print(f"      ✓ Generated encrypted backup share P_{sending_guardian.id}({designated_guardian.id}) for Guardian {designated_guardian.id}")
        
        print(f"      📤 Sending {shares_generated} encrypted backup shares to mediator for distribution")
        mediator.receive_backups(backups)
        print(f"      ✅ Guardian {sending_guardian.id}: Completed backup share generation and submission")
    
    # Distribute Backups via Mediator (Server Distribution)
    print(f"\n   🔄 MEDIATOR: Distributing encrypted backup shares to designated recipients...")
    for designated_guardian in guardians:
        backups = get_optional(mediator.share_backups(designated_guardian.id))
        shares_received = 0
        for backup in backups:
            designated_guardian.save_election_partial_key_backup(backup)
            shares_received += 1
        print(f"   ✓ Guardian {designated_guardian.id}: Received {shares_received} encrypted backup shares from other guardians")
    
    # ROUND 3: Verification of Backup Key Shares
    print(f"\n🔸 ROUND 3: Cryptographic Verification of Received Backup Shares")
    for designated_guardian in guardians:
        verifications = []
        shares_verified = 0
        for backup_owner in guardians:
            if designated_guardian.id != backup_owner.id:
                # Decrypt using auxiliary private key and verify using mathematical proofs
                verification = designated_guardian.verify_election_partial_key_backup(
                    backup_owner.id
                )
                verifications.append(get_optional(verification))
                shares_verified += 1
        
        mediator.receive_backup_verifications(verifications)
        print(f"   ✓ Guardian {designated_guardian.id}: Verified {shares_verified} backup shares using cryptographic proofs")
    
    # FINAL PHASE: Joint Key Publication
    print(f"\n🔸 FINAL PHASE: Publishing Joint Election Key")
    joint_key = get_optional(mediator.publish_joint_key())
    print(f"   ✅ Joint public key published for election encryption")
    print(f"   ✅ Commitment hash generated for election integrity")
    
    # Prepare comprehensive guardian data including complete backup information
    print(f"\n🔸 PREPARING COMPREHENSIVE GUARDIAN DATA WITH BACKUP KEY SHARES")
    guardian_data = []
    private_keys = []
    public_keys = []
    polynomials = []
    
    for guardian in guardians:
        # Collect backup information for threshold reconstruction
        backup_shares_stored = 0
        guardian_info = {
            'id': guardian.id,
            'sequence_order': guardian.sequence_order,
            'election_public_key': to_raw(guardian.share_key()),
            'backups': {}
        }
        
        # Store encrypted backup shares for compensated decryption
        for other_guardian in guardians:
            if other_guardian.id != guardian.id:
                backup = guardian._guardian_election_partial_key_backups.get(other_guardian.id)
                if backup:
                    guardian_info['backups'][other_guardian.id] = to_raw(backup)
                    backup_shares_stored += 1
        
        guardian_data.append(guardian_info)
        print(f"   ✓ Guardian {guardian.id}: Prepared data with {backup_shares_stored} backup shares for threshold reconstruction")
        
        # Store separate keys and polynomials for direct access
        private_keys.append({
            'guardian_id': guardian.id,
            'private_key': str(int(guardian._election_keys.key_pair.secret_key))
        })
        public_keys.append({
            'guardian_id': guardian.id,
            'public_key': str(int(guardian._election_keys.key_pair.public_key))
        })
        polynomials.append({
            'guardian_id': guardian.id,
            'polynomial': to_raw(guardian._election_keys.polynomial)
        })
    
    print(f"\n✅ ELECTIONGUARD BACKUP KEY SHARING CEREMONY COMPLETE")
    print(f"   • All {number_of_guardians} guardians have generated and exchanged encrypted backup key shares")
    print(f"   • Any {quorum} guardians can collaborate to reconstruct missing private keys")
    print(f"   • Election is ready to proceed with threshold security guarantees")
    
    return {
        'guardians': guardians,
        'joint_public_key': str(int(joint_key.joint_public_key)),
        'commitment_hash': str(int(joint_key.commitment_hash)),
        'guardian_data': guardian_data,
        'private_keys': private_keys,
        'public_keys': public_keys,
        'polynomials': polynomials,
        'number_of_guardians': number_of_guardians,
        'quorum': quorum
    }
