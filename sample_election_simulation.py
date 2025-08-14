#!/usr/bin/env python

from typing import Dict, List, Optional, Tuple, Any
import random
from datetime import datetime
import uuid
from collections import defaultdict
import hashlib

# ElectionGuard imports
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
from electionguard.election_polynomial import LagrangeCoefficientsRecord
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
from electionguard.type import BallotId
from electionguard.utils import get_optional
from electionguard.election_polynomial import ElectionPolynomial, Coefficient, SecretCoefficient, PublicCommitment
from electionguard.schnorr import SchnorrProof
from electionguard.elgamal import ElGamalKeyPair, ElGamalPublicKey, ElGamalSecretKey
from electionguard.group import *
from electionguard.decryption_share import DecryptionShare
from electionguard.decryption import compute_decryption_share, compute_decryption_share_for_ballot

# Global variable to track ballot hashes
ballot_hashes = {}

geopolitical_unit = GeopoliticalUnit(
    object_id="county-1",
    name="County 1",
    type=ReportingUnitType.county,
    contact_information=None,
)

ballot_style = BallotStyle(
    object_id="ballot-style-1",
    geopolitical_unit_ids=["county-1"],
    party_ids=None,
    image_uri=None,
)

def generate_ballot_hash(ballot: Any) -> str:
    """Generate a SHA-256 hash for the ballot (works for both encrypted and decrypted ballots)."""
    ballot_bytes = to_raw(ballot).encode('utf-8')
    return hashlib.sha256(ballot_bytes).hexdigest()

def create_election_manifest(
    party_names: List[str], 
    candidate_names: List[str]
) -> Manifest:
    """Create a complete election manifest programmatically."""
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

    contests: List[Contest] = [
        Contest(
            object_id="contest-1",
            sequence_order=0,
            electoral_district_id="county-1",
            vote_variation=VoteVariationType.one_of_m,
            name="County Executive",
            ballot_selections=ballot_selections,
            ballot_title=None,
            ballot_subtitle=None,
            votes_allowed=1,
            number_elected=1,
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

def create_plaintext_ballot(party_names, candidate_names, candidate_name: str, ballot_id: str) -> PlaintextBallot:
    """Create a single plaintext ballot for a specific candidate."""
    manifest = create_election_manifest(
        party_names,
        candidate_names,
    )
    selection = None
    contest = manifest.contests[0]
    for option in contest.ballot_selections:
        if option.candidate_id == candidate_name:
            selection = option
            break
    
    if not selection:
        raise ValueError(f"Candidate {candidate_name} not found in manifest")
    
    ballot_contests = []
    for contest in manifest.contests:
        selections = []
        for option in contest.ballot_selections:
            vote = 1 if option.object_id == selection.object_id else 0
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

def setup_guardians_and_joint_key(number_of_guardians: int, quorum: int) -> Tuple[List[Guardian], ElementModP, ElementModQ]:
    """
    Setup guardians and create joint key.
    Returns list of guardians, the joint public key, and commitment hash.
    """
    print("\n🔹 Setting up guardians and creating joint key")
    
    # Setup Guardians
    guardians: List[Guardian] = []
    for i in range(number_of_guardians):
        guardian = Guardian.from_nonce(
            str(i + 1),  # guardian id
            i + 1,  # sequence order
            number_of_guardians,
            quorum,
        )
        guardians.append(guardian)
        print(f"✅ Created Guardian {i+1} with ID: {guardian.id}")
    
    # Setup Key Ceremony Mediator
    mediator = KeyCeremonyMediator(
        "key-ceremony-mediator", 
        guardians[0].ceremony_details
    )
    
    # ROUND 1: Public Key Sharing
    for guardian in guardians:
        mediator.announce(guardian.share_key())
        print(f"   ✅ Guardian {guardian.id} announced public key")
        
    # Share Keys
    for guardian in guardians:
        announced_keys = get_optional(mediator.share_announced())
        for key in announced_keys:
            if guardian.id != key.owner_id:
                guardian.save_guardian_key(key)
                print(f"   ✅ Guardian {guardian.id} saved key from Guardian {key.owner_id}")
    
    # ROUND 2: Election Partial Key Backup Sharing
    for sending_guardian in guardians:
        sending_guardian.generate_election_partial_key_backups()
        print(f"   ✅ Guardian {sending_guardian.id} generated partial key backups")
        
        backups = []
        for designated_guardian in guardians:
            if designated_guardian.id != sending_guardian.id:
                backup = get_optional(
                    sending_guardian.share_election_partial_key_backup(
                        designated_guardian.id
                    )
                )
                backups.append(backup)
                print(f"   ✅ Guardian {sending_guardian.id} created backup for Guardian {designated_guardian.id}")
        
        mediator.receive_backups(backups)
        print(f"   ✅ Mediator received {len(backups)} backups from Guardian {sending_guardian.id}")
    
    # Receive Backups
    for designated_guardian in guardians:
        backups = get_optional(mediator.share_backups(designated_guardian.id))
        print(f"   ✅ Mediator shared {len(backups)} backups for Guardian {designated_guardian.id}")
        
        for backup in backups:
            designated_guardian.save_election_partial_key_backup(backup)
            print(f"   ✅ Guardian {designated_guardian.id} saved backup from Guardian {backup.owner_id}")
    
    # ROUND 3: Verification of Backups
    for designated_guardian in guardians:
        verifications = []
        for backup_owner in guardians:
            if designated_guardian.id != backup_owner.id:
                verification = designated_guardian.verify_election_partial_key_backup(
                    backup_owner.id
                )
                verifications.append(get_optional(verification))
                print(f"   ✅ Guardian {designated_guardian.id} verified backup from Guardian {backup_owner.id}")
        
        mediator.receive_backup_verifications(verifications)
        print(f"   ✅ Mediator received {len(verifications)} verifications from Guardian {designated_guardian.id}")
    
    # FINAL: Publish Joint Key
    joint_key = get_optional(mediator.publish_joint_key())
    print(f"✅ Joint election key published: {joint_key.joint_public_key}")
    print(f"✅ Commitment hash: {joint_key.commitment_hash}")
    
    guardian_public_keys_json = [int(g._election_keys.key_pair.public_key) for g in guardians]  # List of ElementModP
    guardian_private_keys_json = [int(g._election_keys.key_pair.secret_key) for g in guardians]  # List of ElementModQ 
    guardian_polynomials_json = [to_raw(g._election_keys.polynomial) for g in guardians]
    joint_public_key = ElementModP(joint_key.joint_public_key)
    commitment_hash = ElementModQ(joint_key.commitment_hash)
    return guardian_public_keys_json, guardian_private_keys_json, guardian_polynomials_json, joint_public_key, commitment_hash

def encrypt_ballot(
    party_names,
    candidate_names,
    joint_public_key_json,
    commitment_hash_json,
    plaintext_ballot
) -> Optional[CiphertextBallot]:
    """
    Encrypt a single ballot.
    Returns the encrypted ballot or None if encryption fails.
    """
    joint_public_key = int_to_p(joint_public_key_json)
    commitment_hash = int_to_q(commitment_hash_json)
    manifest = create_election_manifest(
        party_names,
        candidate_names,
    )
    print(f"\n🔹 Encrypting ballot: {plaintext_ballot.object_id}")
    
    # Create election builder and set public key and commitment hash
    election_builder = ElectionBuilder(
        number_of_guardians=1,
        quorum=1,
        manifest=manifest
    )
    election_builder.set_public_key(joint_public_key)
    election_builder.set_commitment_hash(commitment_hash)
    
    # Build the election context
    internal_manifest, context = get_optional(election_builder.build())
    
    # Create encryption device and mediator
    device = EncryptionDevice(device_id=1, session_id=1, launch_code=1, location="polling-place")
    encrypter = EncryptionMediator(internal_manifest, context, device)
    
    # Encrypt the ballot
    encrypted_ballot = encrypter.encrypt(plaintext_ballot)
    if encrypted_ballot:
        encrypted_ballot = get_optional(encrypted_ballot)
        return encrypted_ballot
    else:
        print(f"❌ Failed to encrypt ballot: {plaintext_ballot.object_id}")
        return None

def tally_encrypted_ballots(
    party_names,
    candidate_names,
    joint_public_key_json,
    commitment_hash_json,
    encrypted_ballots_json
) -> Tuple[CiphertextTally, List[SubmittedBallot]]:
    """
    Tally encrypted ballots.
    Returns the ciphertext tally and list of submitted ballots.
    """
    print("\n🔹 Tallying encrypted ballots")
    joint_public_key = int_to_p(joint_public_key_json)
    commitment_hash = int_to_q(commitment_hash_json)
    encrypted_ballots : List[CiphertextBallot] = []
    for encrypted_ballot_json in encrypted_ballots_json:
        encrypted_ballots.append(from_raw(CiphertextBallot, encrypted_ballot_json))
    manifest = create_election_manifest(
        party_names,
        candidate_names,
    )
    
    # Create election builder and set public key and commitment hash
    election_builder = ElectionBuilder(
        number_of_guardians=1,
        quorum=1,
        manifest=manifest
    )
    election_builder.set_public_key(joint_public_key)
    election_builder.set_commitment_hash(commitment_hash)
    
    # Build the election context
    internal_manifest, context = get_optional(election_builder.build())
    
    # Create ballot store and ballot box
    ballot_store = DataStore()
    ballot_box = BallotBox(internal_manifest, context, ballot_store)
    
    # Submit ballots - spoil the first one, cast the rest
    submitted_ballots = []
    for i, ballot in enumerate(encrypted_ballots):
        if i == 0:  # Spoil first ballot
            submitted = ballot_box.spoil(ballot)
            if submitted:
                submitted_ballots.append(get_optional(submitted))
                print(f"🔴 Spoiled ballot: {ballot.object_id} (will not be counted in results)")
        else:  # Cast all other ballots
            submitted = ballot_box.cast(ballot)
            if submitted:
                submitted_ballots.append(get_optional(submitted))
                print(f"🟢 Cast ballot: {ballot.object_id} (will be counted in results)")
    
    # Tally the ballots
    ciphertext_tally = get_optional(
        tally_ballots(ballot_store, internal_manifest, context)
    )
    print(f"✅ Created encrypted tally with {ciphertext_tally.cast()} cast ballots")
    
    ciphertext_tally_json = ciphertext_tally_to_raw(ciphertext_tally)
    submitted_ballots_json = [to_raw(submitted_ballot) for submitted_ballot in submitted_ballots]
    return ciphertext_tally_json, submitted_ballots_json

def compute_tally_share(
        _election_keys: ElectionKeyPair,
        tally: CiphertextTally,
        context: CiphertextElectionContext
    ) -> Optional[DecryptionShare]:
        """Compute the decryption share of tally."""
        return compute_decryption_share(
            _election_keys,
            tally,
            context,
        )

def compute_ballot_shares(
    _election_keys: ElectionKeyPair,
    ballots: List[SubmittedBallot],
    context: CiphertextElectionContext
) -> Dict[BallotId, Optional[DecryptionShare]]:
    """Compute the decryption shares of ballots."""
    shares = {}
    for ballot in ballots:
        share = compute_decryption_share_for_ballot(
            _election_keys,
            ballot,
            context,
        )
        shares[ballot.object_id] = share
    return shares

def compute_guardian_decryption_shares(
    party_names,
    candidate_names,
    guardian_id: str,
    sequence_order: int,
    guardian_public_key: int,
    guardian_private_key: int,
    guardian_polynomial,
    ciphertext_tally_json,
    submitted_ballots_json,
    joint_public_key_json,
    commitment_hash_json,
    number_of_guardians
) -> Tuple[ElectionPublicKey, Optional[DecryptionShare], Dict[BallotId, Optional[DecryptionShare]]]:
    """
    Compute decryption shares for a single guardian.
    Returns the guardian's public key, tally share, and ballot shares.
    """
    # Convert inputs to proper types
    public_key = int_to_p(guardian_public_key)
    private_key = int_to_q(guardian_private_key)
    polynomial = from_raw(ElectionPolynomial, guardian_polynomial)
    
    # Create election key pair for this guardian
    election_key = ElectionKeyPair(
        owner_id=guardian_id,
        sequence_order=sequence_order,
        key_pair=ElGamalKeyPair(private_key, public_key),
        polynomial=polynomial
    )
    manifest = create_election_manifest(party_names, candidate_names)
    election_builder = ElectionBuilder(
        number_of_guardians=number_of_guardians,
        quorum=number_of_guardians,
        manifest=manifest
    )
    
    # Set election parameters
    joint_public_key = int_to_p(joint_public_key_json)
    commitment_hash = int_to_q(commitment_hash_json)
    election_builder.set_public_key(joint_public_key)
    election_builder.set_commitment_hash(commitment_hash)
        
    # Build the election context
    internal_manifest, context = get_optional(election_builder.build())
    ciphertext_tally = raw_to_ciphertext_tally(ciphertext_tally_json, manifest=manifest)
    submitted_ballots = [
        from_raw(SubmittedBallot, ballot_json)
        for ballot_json in submitted_ballots_json
    ]

    # Compute shares
    guardian_public_key = election_key.share()
    tally_share = compute_decryption_share(election_key, ciphertext_tally, context)
    ballot_shares = compute_ballot_shares(election_key, submitted_ballots, context)
    
    print(f"✅ Guardian {guardian_id} computed decryption shares")

    public_key = guardian_public_key

    # Serialize each component
    serialized_public_key = to_raw(public_key) if public_key else None
    serialized_tally_share = to_raw(tally_share) if tally_share else None

    serialized_ballot_shares = {}
    for ballot_id, ballot_share in ballot_shares.items():
        serialized_ballot_shares[ballot_id] = to_raw(ballot_share) if ballot_share else None
    
    return serialized_public_key, serialized_tally_share, serialized_ballot_shares

def combine_decryption_shares(
    party_names: List[str],
    candidate_names: List[str],
    joint_public_key_json: Dict,
    commitment_hash_json: Dict,
    ciphertext_tally_json: Dict,
    submitted_ballots_json: List[Dict],
    guardian_shares: List[Tuple]
) -> Dict[str, Any]:
    """
    Combine decryption shares to produce final election results.
    Returns a complete JSON structure with all election results and verification data.
    """
    # Build election context
    manifest = create_election_manifest(party_names, candidate_names)
    election_builder = ElectionBuilder(
        number_of_guardians=len(guardian_shares),
        quorum=len(guardian_shares),
        manifest=manifest
    )
    joint_public_key = int_to_p(joint_public_key_json)
    commitment_hash = int_to_q(commitment_hash_json)
    election_builder.set_public_key(joint_public_key)
    election_builder.set_commitment_hash(commitment_hash)
    internal_manifest, context = get_optional(election_builder.build())
    
    # Process ciphertext tally and ballots
    ciphertext_tally = raw_to_ciphertext_tally(ciphertext_tally_json, manifest=manifest)
    submitted_ballots = [
        from_raw(SubmittedBallot, ballot_json)
        for ballot_json in submitted_ballots_json
    ]
    
    # Deserialize guardian shares
    deserialized_shares = []
    for serialized_tuple in guardian_shares:
        serialized_public_key, serialized_tally_share, serialized_ballot_shares = serialized_tuple
        public_key = from_raw(ElectionPublicKey, serialized_public_key) if serialized_public_key else None
        tally_share = from_raw(DecryptionShare, serialized_tally_share) if serialized_tally_share else None
        ballot_shares = {
            ballot_id: from_raw(DecryptionShare, serialized_ballot_share) 
            for ballot_id, serialized_ballot_share in serialized_ballot_shares.items()
            if serialized_ballot_share
        }
        deserialized_shares.append((public_key, tally_share, ballot_shares))
    
    # Configure decryption mediator
    decryption_mediator = DecryptionMediator("decryption-mediator", context)
    
    # Add all guardian shares
    for guardian_public_key, tally_share, ballot_shares in deserialized_shares:
        decryption_mediator.announce(
            guardian_public_key,
            get_optional(tally_share),
            ballot_shares
        )
    
    # Get plaintext results
    plaintext_tally = get_optional(decryption_mediator.get_plaintext_tally(ciphertext_tally, manifest))
    plaintext_spoiled_ballots = get_optional(decryption_mediator.get_plaintext_ballots(submitted_ballots, manifest))
    
    # Create sets of cast and spoiled ballot IDs for quick lookup
    cast_ballot_ids = ciphertext_tally.cast_ballot_ids
    spoiled_ballot_ids = ciphertext_tally.spoiled_ballot_ids
    
    # Format the complete results
    results = {
        'election': {
            'name': manifest.name,
            'scope_id': manifest.election_scope_id,
            'type': str(manifest.type),
            'start_date': manifest.start_date.isoformat(),
            'end_date': manifest.end_date.isoformat(),
            'geopolitical_units': [{
                'id': unit.object_id,
                'name': unit.name,
                'type': str(unit.type)
            } for unit in manifest.geopolitical_units],
            'parties': [{
                'id': party.object_id,
                'name': party.name
            } for party in manifest.parties],
            'candidates': [{
                'id': candidate.object_id,
                'name': candidate.name,
                'party_id': candidate.party_id
            } for candidate in manifest.candidates],
            'contests': [{
                'id': contest.object_id,
                'name': contest.name,
                'selections': [{
                    'id': selection.object_id,
                    'candidate_id': selection.candidate_id
                } for selection in contest.ballot_selections]
            } for contest in manifest.contests]
        },
        'results': {
            'total_ballots_cast': len(submitted_ballots),
            'total_valid_ballots': len(cast_ballot_ids),
            'total_spoiled_ballots': len(spoiled_ballot_ids),
            'candidates': {},
            'spoiled_ballots': []
        },
        'verification': {
            'ballots': [],
            'guardians': []
        }
    }
    
    # Process election results
    for contest in plaintext_tally.contests.values():
        for selection in contest.selections.values():
            candidate = selection.object_id
            results['results']['candidates'][candidate] = {
                'votes': selection.tally,
                'percentage': round(selection.tally / len(cast_ballot_ids) * 100, 2) if len(cast_ballot_ids) > 0 else 0
            }
    
    # Process spoiled ballots
    for ballot_id, ballot in plaintext_spoiled_ballots.items():
        if isinstance(ballot, PlaintextBallot):
            ballot_info = {
                'ballot_id': ballot_id,
                'initial_hash': ballot_hashes.get(ballot_id, "N/A"),
                'decrypted_hash': generate_ballot_hash(ballot),
                'status': 'spoiled',
                'selections': []
            }
            
            for contest in ballot.contests:
                for selection in contest.ballot_selections:
                    if selection.vote == 1:
                        ballot_info['selections'].append({
                            'contest_id': contest.object_id,
                            'selection_id': selection.object_id,
                            'vote': selection.vote
                        })
            
            results['results']['spoiled_ballots'].append(ballot_info)
    
    # Add ballot verification information
    for ballot in submitted_ballots:
        ballot_info = {
            'ballot_id': ballot.object_id,
            'initial_hash': ballot_hashes.get(ballot.object_id, 'N/A'),
            'status': 'spoiled' if ballot.object_id in spoiled_ballot_ids else 'cast'
        }
        
        if ballot.object_id in spoiled_ballot_ids:
            spoiled_ballot = plaintext_spoiled_ballots.get(ballot.object_id)
            if spoiled_ballot:
                ballot_info['decrypted_hash'] = generate_ballot_hash(spoiled_ballot)
                ballot_info['verification'] = 'success' if ballot_hashes.get(ballot.object_id) else 'no_initial_hash'
            else:
                ballot_info['decrypted_hash'] = 'N/A'
                ballot_info['verification'] = 'failed'
        else:
            ballot_info['decrypted_hash'] = ballot_hashes.get(ballot.object_id, 'N/A')
            ballot_info['verification'] = 'success' if ballot_hashes.get(ballot.object_id) == ballot_info['decrypted_hash'] else 'hash_mismatch'
        
        results['verification']['ballots'].append(ballot_info)
    
    # Add guardian information
    for i, (guardian_public_key, _, _) in enumerate(deserialized_shares):
        results['verification']['guardians'].append({
            'id': guardian_public_key.owner_id,
            'sequence_order': guardian_public_key.sequence_order,
            'public_key': str(guardian_public_key.key)
        })
    
    return results

def ciphertext_tally_to_raw(tally: CiphertextTally) -> Dict:
    """Convert a CiphertextTally to a raw dictionary for serialization."""
    return {
        "_encryption": to_raw(tally._encryption),
        "cast_ballot_ids": list(tally.cast_ballot_ids),
        "spoiled_ballot_ids": list(tally.spoiled_ballot_ids),
        "contests": {contest_id: to_raw(contest) for contest_id, contest in tally.contests.items()},
        "_internal_manifest": to_raw(tally._internal_manifest),
        "_manifest": to_raw(tally._internal_manifest.manifest)
    }

def raw_to_ciphertext_tally(raw: Dict, manifest: Manifest = None) -> CiphertextTally:
    """Reconstruct a CiphertextTally from its raw dictionary representation."""
    internal_manifest = InternalManifest(manifest)
    
    tally = CiphertextTally(
        object_id=raw.get("object_id", ""),
        _internal_manifest=internal_manifest,
        _encryption=from_raw(CiphertextElectionContext, raw["_encryption"]),
    )
    
    tally.cast_ballot_ids = set(raw["cast_ballot_ids"])
    tally.spoiled_ballot_ids = set(raw["spoiled_ballot_ids"])
    
    tally.contests = {
        contest_id: from_raw(CiphertextTallyContest, contest_raw)
        for contest_id, contest_raw in raw["contests"].items()
    }
    
    return tally

def create_encrypted_ballot(
    party_names,
    candidate_names,
    candidate_name,
    ballot_id,
    joint_public_key_json,
    commitment_hash_json
):
    """Create and encrypt a ballot, print the hash immediately after encryption."""
    ballot = create_plaintext_ballot(party_names, candidate_names, candidate_name, ballot_id)
    encrypted_ballot = encrypt_ballot(party_names, candidate_names, joint_public_key_json, commitment_hash_json, ballot)
    
    if encrypted_ballot:
        # Generate and store hash for the ballot
        ballot_hash = generate_ballot_hash(encrypted_ballot)
        ballot_hashes[encrypted_ballot.object_id] = ballot_hash
        print(f"🔐 Ballot ID: {encrypted_ballot.object_id}, Encrypted Hash: {ballot_hash}")
        
        return to_raw(encrypted_ballot)
    return None

def run_demo(party_names, candidate_names, voter_no, number_of_guardians, quorum):
    """Demonstration of the complete workflow."""
    # Step 1: Setup guardians and create joint key
    guardian_public_keys_json, guardian_private_keys_json, guardian_polynomials_json, joint_public_key_json, commitment_hash_json = setup_guardians_and_joint_key(
        number_of_guardians=number_of_guardians,
        quorum=quorum
    )

    # Step 2: Create and encrypt ballots
    encrypted_ballots = []
    for i in range(voter_no):
        encrypted_ballots.append(create_encrypted_ballot(party_names, candidate_names, "Joe Biden", f"ballot-{i*2}", joint_public_key_json, commitment_hash_json))
        encrypted_ballots.append(create_encrypted_ballot(party_names, candidate_names, "Donald Trump", f"ballot-{i*2 + 1}", joint_public_key_json, commitment_hash_json))
    
    # Step 3: Tally encrypted ballots
    ciphertext_tally_json, submitted_ballots_json = tally_encrypted_ballots(
        party_names, candidate_names, joint_public_key_json, commitment_hash_json, encrypted_ballots
    )
    
    # Step 4: Compute decryption shares from each guardian
    guardian_shares = []
    for i in range(number_of_guardians):
        guardian_id = f"guardian-{i+1}"
        print(f"\n🔹 Computing decryption shares for {guardian_id}")
        
        shares = compute_guardian_decryption_shares(
            party_names=party_names,
            candidate_names=candidate_names,
            guardian_id=guardian_id,
            sequence_order=i+1,
            guardian_public_key=guardian_public_keys_json[i],
            guardian_private_key=guardian_private_keys_json[i],
            guardian_polynomial=guardian_polynomials_json[i],
            ciphertext_tally_json=ciphertext_tally_json,
            submitted_ballots_json=submitted_ballots_json,
            joint_public_key_json=joint_public_key_json,
            commitment_hash_json=commitment_hash_json,
            number_of_guardians=number_of_guardians
        )
        guardian_shares.append(shares)
    
    # Step 5: Combine all shares to get final results
    results = combine_decryption_shares(
        party_names=party_names,
        candidate_names=candidate_names,
        joint_public_key_json=joint_public_key_json,
        commitment_hash_json=commitment_hash_json,
        ciphertext_tally_json=ciphertext_tally_json,
        submitted_ballots_json=submitted_ballots_json,
        guardian_shares=guardian_shares
    )
    
    # Print the complete results in a readable JSON format
    print("\n🎉 Final Election Results:")
    import json
    print(json.dumps(results, indent=2))
    
    print("\n🎉 Demo completed successfully!")


if __name__ == "__main__":
    run_demo(
        party_names=["Party A", "Party B"],
        candidate_names=["Joe Biden", "Donald Trump"], 
        voter_no=2,
        number_of_guardians=3,
        quorum=2)
    print("\n🎉 Demo completed successfully!")