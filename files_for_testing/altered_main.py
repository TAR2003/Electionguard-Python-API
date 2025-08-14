#!/usr/bin/env python

from typing import Dict, List, Optional, Tuple, Any
import random
from datetime import datetime
import uuid
from collections import defaultdict

# ElectionGuard imports
from electionguard.ballot import (
    BallotBoxState,
    CiphertextBallot,
    PlaintextBallot,
    PlaintextBallotSelection,
    PlaintextBallotContest,
    SubmittedBallot,
)
from electionguard.constants import get_constants
from electionguard.data_store import DataStore
from electionguard.decryption_mediator import DecryptionMediator
from electionguard.election import CiphertextElectionContext
from electionguard.election_polynomial import LagrangeCoefficientsRecord
from electionguard.encrypt import EncryptionDevice, EncryptionMediator
from electionguard.guardian import Guardian
from electionguard.key_ceremony_mediator import KeyCeremonyMediator
from electionguard.ballot_box import BallotBox, get_ballots
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
)
from electionguard.type import BallotId
from electionguard.utils import get_optional


# Global variable to track voter choices
voter_choices = defaultdict(dict)

def create_election_manifest() -> Manifest:
    """
    Create a complete election manifest programmatically.
    """
    print("Creating election manifest...")
    
    # Create Geopolitical Units
    geopolitical_units: List[GeopoliticalUnit] = [
        GeopoliticalUnit(
            object_id="county-1",
            name="County 1",
            type=ReportingUnitType.county,
            contact_information=None,
        ),
    ]
    
    # Create Parties
    parties: List[Party] = [
        Party(
            object_id="party-1",
            name="Party One",
            abbreviation="P1",
            color=None,
            logo_uri=None,
        ),
        Party(
            object_id="party-2",
            name="Party Two",
            abbreviation="P2",
            color=None,
            logo_uri=None,
        ),
        Party(
            object_id="party-3",
            name="Party Three",
            abbreviation="P3",
            color=None,
            logo_uri=None,
        ),
        Party(
            object_id="independent",
            name="Independent",
            abbreviation="IND",
            color=None,
            logo_uri=None,
        ),
    ]
    
    # Create Candidates
    candidates: List[Candidate] = [
        Candidate(
            object_id="candidate-1",
            name="Candidate One",
            party_id="party-1",
        ),
        Candidate(
            object_id="candidate-2",
            name="Candidate Two",
            party_id="party-2",
        ),
        Candidate(
            object_id="candidate-3",
            name="Candidate Three",
            party_id="party-3",
        ),
        Candidate(
            object_id="candidate-4",
            name="Candidate Four",
            party_id="party-1",
        ),
        Candidate(
            object_id="candidate-5",
            name="Candidate Five",
            party_id="party-2",
        ),
        Candidate(
            object_id="candidate-6",
            name="Candidate Six",
            party_id="independent",
        ),
    ]
    
    # Create Contests
    contests: List[Contest] = [
        Contest(
            object_id="contest-1",
            sequence_order=0,
            electoral_district_id="county-1",
            vote_variation=VoteVariationType.one_of_m,
            name="County Executive",
            ballot_selections=[
                SelectionDescription(
                    object_id="contest-1-candidate-1",
                    candidate_id="candidate-1",
                    sequence_order=0,
                ),
                SelectionDescription(
                    object_id="contest-1-candidate-2",
                    candidate_id="candidate-2",
                    sequence_order=1,
                ),
                SelectionDescription(
                    object_id="contest-1-candidate-3",
                    candidate_id="candidate-3",
                    sequence_order=2,
                ),
            ],
            ballot_title=None,
            ballot_subtitle=None,
            votes_allowed=1,
            number_elected=1,
        ),
        
    ]
    
    # Create Ballot Styles
    ballot_styles: List[BallotStyle] = [
        BallotStyle(
            object_id="ballot-style-1",
            geopolitical_unit_ids=["county-1"],
            party_ids=None,
            image_uri=None,
        ),
    ]
    
    # Create the Manifest
    manifest = Manifest(
        election_scope_id=f"election-{uuid.uuid4()}",
        spec_version="1.0",
        type=ElectionType.general,
        start_date=datetime.now(),
        end_date=datetime.now(),
        geopolitical_units=geopolitical_units,
        parties=parties,
        candidates=candidates,
        contests=contests,
        ballot_styles=ballot_styles,
        name="Test Election",
        contact_information=None,
    )
    
    print(f"""
        {'-'*40}
        # Election Summary:
        # Scope: {manifest.election_scope_id}
        # Geopolitical Units: {len(manifest.geopolitical_units)}
        # Parties: {len(manifest.parties)}
        # Candidates: {len(manifest.candidates)}
        # Contests: {len(manifest.contests)}
        # Ballot Styles: {len(manifest.ballot_styles)}
        {'='*40}
        # start_date: {manifest.start_date}
        # end_date: {manifest.end_date}
        {'-'*40}
    """)
    
    
    return manifest


def create_plaintext_ballots(manifest: Manifest, ballot_count: int = 20) -> List[PlaintextBallot]:
    """
    Generate plaintext ballots programmatically based on the manifest.
    """
    print(" Starting ballot text generating phase...")
    plaintext_ballots: List[PlaintextBallot] = [] # we have to save the list somewhere
    ballot_styles = manifest.ballot_styles # it is fixed, only one
    print('Ballot styles: ', ballot_styles)
    for i in range(ballot_count):
        # Select a random ballot style
        ballot_style = ballot_styles[0]
        geo_unit_ids = ballot_style.geopolitical_unit_ids
        
        # Find contests for the selected ballot style
        available_contests = [
            contest for contest in manifest.contests 
            if contest.electoral_district_id in geo_unit_ids
        ]
        
        ballot_contests = []
        # For each available contest, create selections
        print('Available contests: ', available_contests)
        for contest in available_contests:
            ballot_selections = []
            
            if contest.vote_variation == VoteVariationType.one_of_m:
                print('In the if loop')
                # Choose one selection for one_of_m contests randomly
                chosen_selection = random.choice(contest.ballot_selections)
                print(i, 'th voter')
                print('Available selections: ', contest.ballot_selections)
                print('Chosed selection: ', chosen_selection)
                
                # Record the voter's choice in our global tracker
                voter_id = f"ballot-{i+1}"
                contest_name = contest.name
                candidate_id = chosen_selection.candidate_id
                candidate = next((c for c in manifest.candidates if c.object_id == candidate_id), None)
                candidate_name = candidate.name if candidate else "Unknown"
                voter_choices[voter_id][contest_name] = candidate_name
                
                for selection in contest.ballot_selections:
                    vote = 1 if selection.object_id == chosen_selection.object_id else 0
                    ballot_selections.append(
                        PlaintextBallotSelection(
                            object_id=selection.object_id,
                            vote=vote,
                            is_placeholder_selection=False,
                        )
                    )
            
            # Add the contest to the ballot
            ballot_contests.append(
                PlaintextBallotContest(
                    object_id=contest.object_id,
                    ballot_selections=ballot_selections
                )
            )
        
        # Create the ballot
        plaintext_ballot = PlaintextBallot(
            object_id=f"ballot-{i+1}",
            style_id=ballot_style.object_id,
            contests=ballot_contests,
        )
        
        plaintext_ballots.append(plaintext_ballot)
    
    print(f"Generated {len(plaintext_ballots)} plaintext ballots")
    return plaintext_ballots


def run_election_demo():
    """
    Run a complete end-to-end ElectionGuard demonstration.
    """
    # Constants for the election setup
    NUMBER_OF_GUARDIANS = 5
    QUORUM = 3
    NUMBER_OF_BALLOTS = 20
    
    print(f"""
    Starting ElectionGuard End-to-End Demo
    Number of Guardians: {NUMBER_OF_GUARDIANS}
    Quorum Required: {QUORUM}
    Number of Ballots: {NUMBER_OF_BALLOTS}
    """)
    
    # Step 0: Configure Election
    print("\n🔹 STEP 0: Configuring Election")
    manifest = create_election_manifest()
    
    # Create election builder
    election_builder = ElectionBuilder(
        NUMBER_OF_GUARDIANS, 
        QUORUM,
        manifest
    )
    # election builder use the election manifest to configure the election
    
    print("✅ Election builder created")
    
    # Step 1: Key Ceremony
    print("\n🔹 STEP 1: Conducting Key Ceremony")
    
    # Setup Guardians
    guardians: List[Guardian] = []
    for i in range(NUMBER_OF_GUARDIANS):
        guardian = Guardian.from_nonce(
            str(i + 1),  # guardian id
            i + 1,  # sequence order
            NUMBER_OF_GUARDIANS,
            QUORUM,
        )
        guardians.append(guardian)
        print(f"✅ Created Guardian {i+1} with ID: {guardian.id}")
    
    # Setup Key Ceremony Mediator
    mediator = KeyCeremonyMediator(
        "key-ceremony-mediator", 
        guardians[0].ceremony_details
    )
    print('Ceremony Details:' , guardians[0].ceremony_details)
    # ROUND 1: Public Key Sharing
    print("\n   Round 1: Public Key Sharing")
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
                
    
    all_announced = mediator.all_guardians_announced()
    print(f"   ✅ All guardians announced their public keys: {all_announced}")
    
    # ROUND 2: Election Partial Key Backup Sharing
    print("\n   Round 2: Election Partial Key Backup Sharing")
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
    
    all_backups_available = mediator.all_backups_available()
    print(f"   ✅ All backups available: {all_backups_available}")
    
    # Receive Backups
    for designated_guardian in guardians:
        backups = get_optional(mediator.share_backups(designated_guardian.id))
        print(f"   ✅ Mediator shared {len(backups)} backups for Guardian {designated_guardian.id}")
        
        for backup in backups:
            designated_guardian.save_election_partial_key_backup(backup)
            print(f"   ✅ Guardian {designated_guardian.id} saved backup from Guardian {backup.owner_id}")
    
    # ROUND 3: Verification of Backups
    print("\n   Round 3: Verification of Backups")
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
    
    all_backups_verified = mediator.all_backups_verified()
    print(f"   ✅ All backups verified: {all_backups_verified}")
    
    # FINAL: Publish Joint Key
    joint_key = get_optional(mediator.publish_joint_key())
    print(f"   ✅ Joint election key published: {joint_key.joint_public_key}")
    # Print all guardians' keys
    print("\n🔹 Printing all guardians' keys:")
    for guardian in guardians:
        guardian_key = guardian.share_key()
        print(f"Guardian's {guardian.id} Key::: {guardian_key.key}")

    
    # Set the joint key and commitment hash in the election builder
    election_builder.set_public_key(joint_key.joint_public_key)
    election_builder.set_commitment_hash(joint_key.commitment_hash)
    
    # Build the election
    internal_manifest, context = get_optional(election_builder.build())
    constants = get_constants()
    print('constants:', constants)
    
    print("✅ Election successfully built with joint key")
    
    # Step 2: Encrypt Votes
    print("\n🔹 STEP 2: Encrypting Votes")
    
    # Create an encryption device
    device = EncryptionDevice(device_id=1, session_id=1, launch_code=1, location="polling-place")
    print(f"✅ Created encryption device with ID: {device.device_id}")
    
    # Create an encryption mediator
    encrypter = EncryptionMediator(internal_manifest, context, device)
    print("✅ Created encryption mediator")
    
    # Generate plaintext ballots
    plaintext_ballots = create_plaintext_ballots(manifest, NUMBER_OF_BALLOTS)
    print('All the plain text ballots := ', plaintext_ballots )

    # Encrypt ballots
    ciphertext_ballots: List[CiphertextBallot] = []
    for plaintext_ballot in plaintext_ballots:
        encrypted_ballot = encrypter.encrypt(plaintext_ballot)
        if encrypted_ballot:
            ciphertext_ballot = get_optional(encrypted_ballot)
            ciphertext_ballots.append(ciphertext_ballot)
            print(f"✅ Encrypted ballot: {plaintext_ballot.object_id}")
        else:
            print(f"❌ Failed to encrypt ballot: {plaintext_ballot.object_id}")
    
    print(f"✅ Encrypted {len(ciphertext_ballots)} ballots")
    
    # Step 3: Cast and Spoil Ballots
    print("\n🔹 STEP 3: Casting and Spoiling Ballots")
    
    # Create a ballot store
    ballot_store = DataStore()
    
    # Create a ballot box
    ballot_box = BallotBox(internal_manifest, context, ballot_store)
    print("✅ Created ballot box")
    
    # Cast or spoil each ballot randomly
    cast_count = 0
    spoiled_count = 0
    
    for ballot in ciphertext_ballots:
        # Randomly decide to cast or spoil
        if random.randint(0, 1):
            # Cast the ballot
            submitted_ballot = ballot_box.cast(ballot)
            if submitted_ballot:
                cast_count += 1
                print(f"✅ Cast ballot: {ballot.object_id}")
            else:
                print(f"❌ Failed to cast ballot: {ballot.object_id}")
        else:
            # Spoil the ballot
            submitted_ballot = ballot_box.spoil(ballot)
            if submitted_ballot:
                spoiled_count += 1
                print(f"✅ Spoiled ballot: {ballot.object_id}")
            else:
                print(f"❌ Failed to spoil ballot: {ballot.object_id}")
    
    print(f"✅ Processed {cast_count} cast ballots and {spoiled_count} spoiled ballots")
    
    # Step 4: Decrypt Tally
    print("\n🔹 STEP 4: Tallying and Decrypting Results")
    
    # Tally the ballots
    ciphertext_tally = get_optional(
        tally_ballots(ballot_store, internal_manifest, context)
    )
    print(f"✅ Created encrypted tally with {ciphertext_tally.cast()} cast ballots")
    
    # Get spoiled ballots
    submitted_ballots = get_ballots(ballot_store, BallotBoxState.SPOILED)
    print(f"✅ Retrieved {len(submitted_ballots)} spoiled ballots for decryption")
    
    # Configure the Decryption Mediator
    decryption_mediator = DecryptionMediator(
        "decryption-mediator",
        context,
    )
    print("✅ Created decryption mediator")
    
    # Have each guardian participate in the decryption
    submitted_ballots_list = list(submitted_ballots.values())
    
    for guardian in guardians:
        # Each guardian computes their share of the tally
        guardian_key = guardian.share_key()
        tally_share = guardian.compute_tally_share(ciphertext_tally, context)
        ballot_shares = guardian.compute_ballot_shares(submitted_ballots_list, context)
        
        # Guardian announces their share
        decryption_mediator.announce(
            guardian_key, 
            get_optional(tally_share),
            ballot_shares
        )
        print(f"✅ Guardian {guardian.id} computed and shared tally & ballot decryption shares")
    
    lagrange_coefficients = LagrangeCoefficientsRecord(
        decryption_mediator.get_lagrange_coefficients()
    )
    print("✅ Generated Lagrange coefficients for decryption")
    
    # Get the plaintext tally
    plaintext_tally = get_optional(
        decryption_mediator.get_plaintext_tally(ciphertext_tally, manifest)
    )
    print("✅ Successfully decrypted tally")
    
    # Get the plaintext spoiled ballots
    plaintext_spoiled_ballots = get_optional(
        decryption_mediator.get_plaintext_ballots(submitted_ballots_list, manifest)
    )
    print(f"✅ Successfully decrypted {len(plaintext_spoiled_ballots)} spoiled ballots")
    
    # Step 5: Verify and Display Results
    print("\n🔹 STEP 5: Verifying and Displaying Results")
    
    # First print the voter choices
    print("\n🗳️ Voter Choices:")
    for voter_id, choices in voter_choices.items():
        print(f"\nVoter {voter_id} voted:")
        for contest, candidate in choices.items():
            print(f"  - {contest}: {candidate}")
    
    # Create a map of ballot IDs to plaintext ballots for easy lookup
    plaintext_ballot_map = {ballot.object_id: ballot for ballot in plaintext_ballots}
    
    # Verify that the tally matches the expected results
    print("\n📊 Election Results:\n")
    
    # Create a representation of each contest's tally from plaintext ballots
    selection_ids = [
        selection.object_id
        for contest in manifest.contests
        for selection in contest.ballot_selections
    ]
    expected_plaintext_tally: Dict[str, int] = {key: 0 for key in selection_ids}
    
    # Tally the expected values from the cast ballots
    for ballot in plaintext_ballots:
        submitted_ballot = ballot_store.get(ballot.object_id)
        if submitted_ballot and get_optional(submitted_ballot).state == BallotBoxState.CAST:
            for contest in ballot.contests:
                for selection in contest.ballot_selections:
                    expected_plaintext_tally[selection.object_id] += selection.vote
    
    # Compare the expected tally to the decrypted tally
    print("Contest Results:")
    for contest in manifest.contests:
        print(f"\n  Contest: {contest.object_id} - {contest.name}")
        contest_results = plaintext_tally.contests.get(contest.object_id)
        
        if contest_results:
            for selection in contest.ballot_selections:
                candidate = next((c for c in manifest.candidates if c.object_id == selection.candidate_id), None)
                candidate_name = candidate.name if candidate else "Unknown Candidate"
                party = next((p for p in manifest.parties if candidate and p.object_id == candidate.party_id), None)
                party_name = f" ({party.name})" if party else ""
                
                decrypted_vote_count = contest_results.selections[selection.object_id].tally
                expected_vote_count = expected_plaintext_tally[selection.object_id]
                
                print(f"    {candidate_name}{party_name}: {decrypted_vote_count} votes")
                
                # Verify the count matches
                if decrypted_vote_count != expected_vote_count:
                    print(f"    ❌ WARNING: Expected {expected_vote_count}, got {decrypted_vote_count}")
                else:
                    print(f"    ✓ Verified: Decrypted count matches expected count")
        else:
            print("    No results available for this contest")
    
    # Verify spoiled ballots
    if plaintext_spoiled_ballots:
        print("\n🧾 Spoiled Ballot Verification:")
        spoiled_count = 0
        verified_count = 0
        
        for ballot_id, spoiled_tally in plaintext_spoiled_ballots.items():
            spoiled_count += 1
            original_ballot = plaintext_ballot_map.get(ballot_id)
            
            if original_ballot:
                all_verified = True
                
                for contest in original_ballot.contests:
                    spoiled_contest = spoiled_tally.contests.get(contest.object_id)
                    
                    if spoiled_contest:
                        for selection in contest.ballot_selections:
                            expected_vote = selection.vote
                            decrypted_vote = spoiled_contest.selections[selection.object_id].tally
                            
                            if expected_vote != decrypted_vote:
                                all_verified = False
                                print(f"  ❌ Ballot {ballot_id}, Selection {selection.object_id}: Expected {expected_vote}, got {decrypted_vote}")
                
                if all_verified:
                    verified_count += 1
            else:
                print(f"  ❌ Could not find original ballot {ballot_id}")
        
        print(f"\n✅ Verified {verified_count} of {spoiled_count} spoiled ballots")
    
    print("\n✅ ElectionGuard end-to-end demo completed successfully")


if __name__ == "__main__":
    run_election_demo()