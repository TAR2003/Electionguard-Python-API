#!/usr/bin/env python

from typing import Dict, List, Optional, Tuple, Any
import random
from datetime import datetime, timedelta
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

def get_input(prompt: str, default: str = "") -> str:
    """Helper function to get user input with a default value."""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    response = input(prompt).strip()
    return response if response else default

def get_int_input(prompt: str, default: int = 0) -> int:
    """Helper function to get integer input with a default value."""
    while True:
        try:
            response = input(f"{prompt} [{default}]: ").strip()
            return int(response) if response else default
        except ValueError:
            print("Please enter a valid number.")

def get_yes_no_input(prompt: str, default: bool = True) -> bool:
    """Helper function to get yes/no input with a default value."""
    while True:
        response = input(f"{prompt} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
        if not response:
            return default
        if response in ('y', 'yes'):
            return True
        if response in ('n', 'no'):
            return False
        print("Please enter 'y' or 'n'.")

def create_election_manifest_interactive() -> Manifest:
    """Create an election manifest interactively with user input."""
    print("\n=== Election Configuration ===")
    
    # Basic election info
    election_title = get_input("Enter election title", "General Election 2023")
    election_scope = get_input("Enter election scope ID", f"election-{uuid.uuid4()}")

    # We have added the title and scope from the user input
    
    # Election dates
    start_date = datetime.now()
    # The start date is now
    end_date = start_date + timedelta(days=1)
    # We are adding one day to set the end time from the election exactly 1 day from now (start time)
    print(f"Election dates: {start_date} to {end_date}")
    
    # Create geopolitical units
    print("\n=== Geopolitical Units ===")
    geopolitical_units = []
    num_units = get_int_input("Enter number of geopolitical units", 2)
    # This is the geopolitical units
    for i in range(num_units):
        print(f"\nGeopolitical Unit {i+1}:")
        unit_id = get_input("  Enter unit ID", f"unit-{i+1}")
        name = get_input("  Enter unit name", f"District {i+1}")
        unit_type = get_input("  Enter unit type (county, state, etc.)", "county")
        # GeopoliticalUnit class contains object_id, name, type, contact_information elements
        geopolitical_units.append(
            GeopoliticalUnit(
                object_id=unit_id,
                name=name,
                type=ReportingUnitType.county,
                contact_information=None,
            )
        )
        print(f"Added {name} ({unit_id})")
    
    # Create parties
    print("\n=== Political Parties ===")
    parties = []
    num_parties = get_int_input("Enter number of political parties", 2)
    # Now adding the political parties
    for i in range(num_parties):
        print(f"\nParty {i+1}:") # We can select the serial number as the party id
        party_id = get_input("  Enter party ID", f"party-{i+1}")
        name = get_input("  Enter party name", f"Party {i+1}") # we can select the party name
        abbreviation = get_input("  Enter party abbreviation", name[:3].upper())
        
        parties.append(
            Party(
                object_id=party_id,
                name=name,
                abbreviation=abbreviation,
                color=None,
                logo_uri=None,
            ) # the party class needed object_id, name, abbreviation, color, logo_uri
        )
        print(f"Added {name} ({abbreviation})")
    
    # Create candidates
    print("\n=== Candidates ===")
    candidates = []
    num_candidates = get_int_input("Enter number of candidates", 3)
    
    for i in range(num_candidates):
        print(f"\nCandidate {i+1}:")
        candidate_id = get_input("  Enter candidate ID", f"candidate-{i+1}")
        name = get_input("  Enter candidate name", f"Candidate {i+1}")
        
        # Show available parties
        print("  Available parties:")
        for j, party in enumerate(parties):
            print(f"    {j+1}. {party.name} ({party.abbreviation})")
        
        party_choice = get_int_input("  Select party number", 1)
        if party_choice < 1 or party_choice > len(parties):
            print("Invalid party selection, using first party")
            party_choice = 1
        
        candidates.append(
            Candidate(
                object_id=candidate_id,
                name=name,
                party_id=parties[party_choice-1].object_id,
            ) # Candidate class needs object_id, name, party_id
        )
        print(f"Added {name} ({parties[party_choice-1].abbreviation})")
    
    # Create contests
    print("\n=== Contests ===")
    contests = []
    num_contests = get_int_input("Enter number of contests", 2) # generally we would prefer the contest number to be one
    
    for i in range(num_contests):
        print(f"\nContest {i+1}:")
        contest_id = get_input("  Enter contest ID", f"contest-{i+1}") #contest id is the user input serial number, which might be unnecessary
        
        # Select geopolitical unit
        print("  Available geopolitical units:")
        for j, unit in enumerate(geopolitical_units):
            print(f"    {j+1}. {unit.name} ({unit.object_id})") # We can fix the only one geopolitical unit for a certain election
        
        # We have to make the geopoliticalUnit default to the first one because we might not need this on a web app
        unit_choice = get_int_input("  Select geopolitical unit number", 1)
        if unit_choice < 1 or unit_choice > len(geopolitical_units):
            print("Invalid selection, using first unit")
            unit_choice = 1
        
        name = get_input("  Enter contest name", f"Contest {i+1}")
        votes_allowed = get_int_input("  Enter number of votes allowed", 1)
        number_elected = get_int_input("  Enter number of candidates to be elected", 1)
        
        # Create selections
        selections = []
        print("  Available candidates:") # available candidate number
        for j, candidate in enumerate(candidates):
            party = next((p for p in parties if p.object_id == candidate.party_id), None)
            party_name = f" ({party.abbreviation})" if party else ""
            print(f"    {j+1}. {candidate.name}{party_name}")
        
        num_selections = get_int_input("  How many candidates will be in this contest?", min(3, len(candidates)))
        # it will determine how many of the candidates we will keep on our list
        # we can set it to default all of them
        for j in range(num_selections):
            candidate_choice = get_int_input(f"  Select candidate {j+1} (number)", j+1)
            if candidate_choice < 1 or candidate_choice > len(candidates):
                print("Invalid candidate selection, skipped")
                continue
            
            selections.append(
                SelectionDescription(
                    object_id=f"{contest_id}-selection-{j+1}",
                    candidate_id=candidates[candidate_choice-1].object_id,
                    sequence_order=j,
                ) # SelectionDescription needs object_id, candidate_id, sequence_order
            )
            print(f"  Added {candidates[candidate_choice-1].name}")
        
        contests.append(
            Contest(
                object_id=contest_id,
                sequence_order=i,
                electoral_district_id=geopolitical_units[unit_choice-1].object_id,
                vote_variation=VoteVariationType.one_of_m,
                name=name,
                ballot_selections=selections,
                ballot_title=None,
                ballot_subtitle=None,
                votes_allowed=votes_allowed,
                number_elected=number_elected,
            ) # Contest needs object_id, sequence_order, electoral_district_id, vote_variation, name, ballot_selections, ballot_title, ballot_subtitle, votes_allowed, number_elected
        )
        print(f"Added contest: {name} with {len(selections)} candidates")
    
    # Create ballot styles
    print("\n=== Ballot Styles ===")
    ballot_styles = []
    num_styles = get_int_input("Enter number of ballot styles", 2)
    
    for i in range(num_styles):
        print(f"\nBallot Style {i+1}:")
        style_id = get_input("  Enter ballot style ID", f"style-{i+1}")
        
        # Select geopolitical units
        print("  Available geopolitical units:") # we can set it to default 1
        for j, unit in enumerate(geopolitical_units):
            print(f"    {j+1}. {unit.name} ({unit.object_id})")
        
        selected_units = []
        num_units_in_style = get_int_input("  How many units will be in this ballot style?", 1)
        # we can just fix it to be 1, because geopolitical unit might not be a necessary feature in a web application
        for j in range(num_units_in_style):
            unit_choice = get_int_input(f"  Select unit {j+1} (number)", j+1)
            if unit_choice < 1 or unit_choice > len(geopolitical_units):
                print("Invalid selection, skipped")
                continue
            
            selected_units.append(geopolitical_units[unit_choice-1].object_id)
            print(f"  Added {geopolitical_units[unit_choice-1].name}")
        
        ballot_styles.append(
            BallotStyle(
                object_id=style_id,
                geopolitical_unit_ids=selected_units,
                party_ids=None,
                image_uri=None,
            ) # BallotStyle needs object_id, geopolitical_unit_ids, party_ids, image_uri
        )
        print(f"Added ballot style {style_id} with {len(selected_units)} units")
    
    # Create the manifest
    manifest = Manifest(
        election_scope_id=election_scope,
        spec_version=SpecVersion.EG0_95,
        type=ElectionType.general,
        start_date=start_date,
        end_date=end_date,
        geopolitical_units=geopolitical_units,
        parties=parties,
        candidates=candidates,
        contests=contests,
        ballot_styles=ballot_styles,
        name=election_title,
        contact_information=None,
    ) # Creating the election Manifest
    
    print("\n=== Election Summary ===")
    print(f"Title: {manifest.name}")
    print(f"Scope ID: {manifest.election_scope_id}")
    print(f"Dates: {manifest.start_date} to {manifest.end_date}")
    print(f"Geopolitical Units: {len(manifest.geopolitical_units)}")
    print(f"Parties: {len(manifest.parties)}")
    print(f"Candidates: {len(manifest.candidates)}")
    print(f"Contests: {len(manifest.contests)}")
    print(f"Ballot Styles: {len(manifest.ballot_styles)}")
    
    return manifest # manifest is the total necessary information to create an election


def interactive_key_ceremony(number_of_guardians: int, quorum: int) -> Tuple[List[Guardian], Any]:
    """Conduct an interactive key ceremony."""
    print("\n=== Key Ceremony ===")
    # We are inside the key ceremony process it seems
    # Create guardians
    guardians = []
    for i in range(number_of_guardians):
        print(f"\nGuardian {i+1} setup:")
        guardian_id = get_input(f"  Enter ID for guardian {i+1}", str(i+1))
        sequence_order = i + 1
        
        guardian = Guardian.from_nonce(
            guardian_id,
            sequence_order,
            number_of_guardians,
            quorum,
        ) # making of a guardian class element 
        guardians.append(guardian)
        print(f"✅ Created Guardian {guardian.id}")
    
    # Setup Key Ceremony Mediator
    mediator = KeyCeremonyMediator(
        "key-ceremony-mediator", 
        guardians[0].ceremony_details
    )
    
    # ROUND 1: Public Key Sharing
    print("\n🔹 ROUND 1: Public Key Sharing")
    for guardian in guardians:
        mediator.announce(guardian.share_key())
        print(f"✅ Guardian {guardian.id} announced public key")
    # Announce Keys
    # Share Keys
    for guardian in guardians:
        announced_keys = get_optional(mediator.share_announced())
        for key in announced_keys:
            if guardian.id != key.owner_id:
                guardian.save_guardian_key(key)
                print(f"✅ Guardian {guardian.id} saved key from Guardian {key.owner_id}")
    
    # ROUND 2: Partial Key Backup Sharing
    print("\n🔹 ROUND 2: Partial Key Backup Sharing")
    for sending_guardian in guardians:
        print(f"\nGuardian {sending_guardian.id} is generating backups...")
        sending_guardian.generate_election_partial_key_backups()
        
        backups = []
        for designated_guardian in guardians:
            if designated_guardian.id != sending_guardian.id:
                print(f"  Creating backup for Guardian {designated_guardian.id}")
                backup = get_optional(
                    sending_guardian.share_election_partial_key_backup(
                        designated_guardian.id
                    )
                )
                backups.append(backup)
        
        mediator.receive_backups(backups)
        print(f"✅ Mediator received {len(backups)} backups from Guardian {sending_guardian.id}")
    
    # Receive Backups
    for designated_guardian in guardians:
        backups = get_optional(mediator.share_backups(designated_guardian.id))
        print(f"\nGuardian {designated_guardian.id} is receiving backups...")
        
        for backup in backups:
            print(f"  Processing backup from Guardian {backup.owner_id}")
            designated_guardian.save_election_partial_key_backup(backup)
        
        print(f"✅ Guardian {designated_guardian.id} processed {len(backups)} backups")
    
    # ROUND 3: Verification of Backups
    print("\n🔹 ROUND 3: Verification of Backups")
    for designated_guardian in guardians:
        print(f"\nGuardian {designated_guardian.id} is verifying backups...")
        verifications = []
        
        for backup_owner in guardians:
            if designated_guardian.id != backup_owner.id:
                print(f"  Verifying backup from Guardian {backup_owner.id}")
                verification = designated_guardian.verify_election_partial_key_backup(
                    backup_owner.id
                )
                verifications.append(get_optional(verification))
        
        mediator.receive_backup_verifications(verifications)
        print(f"✅ Mediator received {len(verifications)} verifications from Guardian {designated_guardian.id}")
    
    # FINAL: Publish Joint Key
    print("\n🔹 FINAL: Publishing Joint Key")
    joint_key = get_optional(mediator.publish_joint_key())
    print(f"✅ Joint election key published: {joint_key.joint_public_key}")
    
    return guardians, joint_key

def interactive_voting(manifest: Manifest, context: CiphertextElectionContext) -> Tuple[List[PlaintextBallot], List[CiphertextBallot]]:
    """Conduct interactive voting."""
    print("\n=== Voting Process ===")
    
    # Create encryption device and mediator
    device = EncryptionDevice(device_id=1, session_id=1, launch_code=1, location="polling-place")
    internal_manifest = InternalManifest(manifest)
    encrypter = EncryptionMediator(internal_manifest, context, device)
    
    # Get number of voters
    num_voters = get_int_input("Enter number of voters", 5)
    
    plaintext_ballots = []
    ciphertext_ballots = []
    
    for i in range(num_voters):
        print(f"\n=== Voter {i+1} ===")
        
        # Select ballot style
        print("Available ballot styles:")
        for j, style in enumerate(manifest.ballot_styles):
            print(f"  {j+1}. {style.object_id} (Units: {', '.join(style.geopolitical_unit_ids)})")
        
        style_choice = get_int_input("Select ballot style", 1)
        if style_choice < 1 or style_choice > len(manifest.ballot_styles):
            print("Invalid selection, using first style")
            style_choice = 1
        
        ballot_style = manifest.ballot_styles[style_choice-1]
        geo_unit_ids = ballot_style.geopolitical_unit_ids
        
        # Find contests for this ballot style
        available_contests = [
            contest for contest in manifest.contests 
            if contest.electoral_district_id in geo_unit_ids
        ]
        
        ballot_contests = []
        
        for contest in available_contests:
            print(f"\nContest: {contest.name}")
            print(f"Vote for {contest.number_elected} of {len(contest.ballot_selections)} candidates")
            
            # Show candidates
            selections = []
            for j, selection in enumerate(contest.ballot_selections):
                candidate = next((c for c in manifest.candidates if c.object_id == selection.candidate_id), None)
                party = next((p for p in manifest.parties if candidate and p.object_id == candidate.party_id), None)
                party_name = f" ({party.name})" if party else ""
                print(f"  {j+1}. {candidate.name if candidate else 'Unknown'}{party_name}")
            
            # Get votes
            votes = []
            for _ in range(contest.number_elected):
                choice = get_int_input("  Enter your choice (number)", 1)
                if choice < 1 or choice > len(contest.ballot_selections):
                    print("Invalid choice, skipped")
                    continue
                votes.append(choice-1)
            
            # Create selections
            ballot_selections = []
            for j, selection in enumerate(contest.ballot_selections):
                vote = 1 if j in votes else 0
                ballot_selections.append(
                    PlaintextBallotSelection(
                        object_id=selection.object_id,
                        vote=vote,
                        is_placeholder_selection=False,
                    )
                )
            
            ballot_contests.append(
                PlaintextBallotContest(
                    object_id=contest.object_id,
                    ballot_selections=ballot_selections
                )
            )
        
        # Create and encrypt ballot
        plaintext_ballot = PlaintextBallot(
            object_id=f"ballot-{i+1}",
            style_id=ballot_style.object_id,
            contests=ballot_contests,
        )
        
        encrypted_ballot = encrypter.encrypt(plaintext_ballot)
        if encrypted_ballot:
            ciphertext_ballot = get_optional(encrypted_ballot)
            plaintext_ballots.append(plaintext_ballot)
            ciphertext_ballots.append(ciphertext_ballot)
            print(f"✅ Ballot encrypted and submitted")
        else:
            print("❌ Failed to encrypt ballot")
    
    return plaintext_ballots, ciphertext_ballots

def interactive_decryption(guardians: List[Guardian], manifest: Manifest, 
                         context: CiphertextElectionContext, 
                         ciphertext_tally: CiphertextTally) -> PlaintextTally:
    """Conduct interactive decryption."""
    print("\n=== Decryption Process ===")
    
    # Setup decryption mediator
    decryption_mediator = DecryptionMediator(
        "decryption-mediator",
        context,
    )
    
    # Collect decryption shares from guardians
    available_guardians = guardians.copy()
    while True:
        print("\nAvailable guardians:")
        for i, guardian in enumerate(available_guardians):
            print(f"  {i+1}. {guardian.id}")
        
        print("\nOptions:")
        print("  1. Add guardian decryption share")
        print("  2. Complete decryption")
        
        choice = get_int_input("Select option", 1)
        
        if choice == 1:
            # Add guardian share
            guardian_choice = get_int_input("Select guardian to add share", 1)
            if guardian_choice < 1 or guardian_choice > len(available_guardians):
                print("Invalid selection")
                continue
            
            guardian = available_guardians[guardian_choice-1]
            
            # Guardian computes their share
            guardian_key = guardian.share_key()
            tally_share = guardian.compute_tally_share(ciphertext_tally, context)
            
            # Add to mediator with empty dictionary for ballot shares
            decryption_mediator.announce(
                guardian_key, 
                get_optional(tally_share),
                {}  # Changed from [] to {}
            )
            
            print(f"✅ Guardian {guardian.id} added decryption share")
            available_guardians.pop(guardian_choice-1)
        
        elif choice == 2:
            # Complete decryption
            if len(decryption_mediator.get_available_guardians()) < context.quorum:
                print(f"❌ Need at least {context.quorum} guardians for decryption")
                continue
            
            # Get Lagrange coefficients
            lagrange_coefficients = LagrangeCoefficientsRecord(
                decryption_mediator.get_lagrange_coefficients()
            )
            
            # Decrypt the tally
            plaintext_tally = get_optional(
                decryption_mediator.get_plaintext_tally(ciphertext_tally, manifest)
            )
            
            if plaintext_tally:
                print("✅ Successfully decrypted tally")
                return plaintext_tally
            else:
                print("❌ Failed to decrypt tally")
                continue
        
        else:
            print("Invalid choice")
def run_interactive_election():
    """Run an interactive election demo."""
    print("""
    ====================================
    ELECTIONGUARD INTERACTIVE DEMO
    ====================================
    """)
    
    # Step 1: Configure Election
    print("\n=== STEP 1: Configure Election ===")
    manifest = create_election_manifest_interactive()
    
    # Get guardian parameters
    number_of_guardians = get_int_input("\nEnter number of guardians", 3)
    quorum = get_int_input("Enter quorum required for decryption", 2)
    if quorum > number_of_guardians:
        print("Quorum cannot exceed number of guardians, setting to number of guardians")
        quorum = number_of_guardians
    
    # Step 2: Key Ceremony
    print("\n=== STEP 2: Key Ceremony ===")
    guardians, joint_key = interactive_key_ceremony(number_of_guardians, quorum)
    
    # Build election context
    election_builder = ElectionBuilder(
        number_of_guardians, 
        quorum,
        manifest
    )
    election_builder.set_public_key(joint_key.joint_public_key)
    election_builder.set_commitment_hash(joint_key.commitment_hash)
    internal_manifest, context = get_optional(election_builder.build())
    
    # Step 3: Voting
    print("\n=== STEP 3: Voting ===")
    plaintext_ballots, ciphertext_ballots = interactive_voting(manifest, context)
    
    # Step 4: Tallying
    print("\n=== STEP 4: Tallying ===")
    ballot_store = DataStore()
    ballot_box = BallotBox(internal_manifest, context, ballot_store)
    
    # Cast all ballots
    for ballot in ciphertext_ballots:
        submitted_ballot = ballot_box.cast(ballot)
        if submitted_ballot:
            print(f"✅ Cast ballot: {ballot.object_id}")
        else:
            print(f"❌ Failed to cast ballot: {ballot.object_id}")
    
    # Tally the ballots
    ciphertext_tally = get_optional(
        tally_ballots(ballot_store, internal_manifest, context)
    )
    print(f"\n✅ Created encrypted tally with {ciphertext_tally.cast()} cast ballots")
    
    # Step 5: Decryption
    print("\n=== STEP 5: Decryption ===")
    plaintext_tally = interactive_decryption(guardians, manifest, context, ciphertext_tally)
    
    # Step 6: Results
    print("\n=== ELECTION RESULTS ===")
    print("\nContest Results:")
    for contest in manifest.contests:
        print(f"\nContest: {contest.name}")
        contest_results = plaintext_tally.contests.get(contest.object_id)
        
        if contest_results:
            for selection in contest.ballot_selections:
                candidate = next((c for c in manifest.candidates if c.object_id == selection.candidate_id), None)
                party = next((p for p in manifest.parties if candidate and p.object_id == candidate.party_id), None)
                party_name = f" ({party.name})" if party else ""
                
                vote_count = contest_results.selections[selection.object_id].tally
                print(f"  {candidate.name if candidate else 'Unknown'}{party_name}: {vote_count} votes")
        else:
            print("  No results available")
    
    print("\n=== ELECTION COMPLETE ===")

if __name__ == "__main__":
    run_interactive_election()#!/usr/bin/env python

from typing import Dict, List, Optional, Tuple, Any
import random
from datetime import datetime, timedelta
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

def get_input(prompt: str, default: str = "") -> str:
    """Helper function to get user input with a default value."""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    response = input(prompt).strip()
    return response if response else default

def get_int_input(prompt: str, default: int = 0) -> int:
    """Helper function to get integer input with a default value."""
    while True:
        try:
            response = input(f"{prompt} [{default}]: ").strip()
            return int(response) if response else default
        except ValueError:
            print("Please enter a valid number.")

def get_yes_no_input(prompt: str, default: bool = True) -> bool:
    """Helper function to get yes/no input with a default value."""
    while True:
        response = input(f"{prompt} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
        if not response:
            return default
        if response in ('y', 'yes'):
            return True
        if response in ('n', 'no'):
            return False
        print("Please enter 'y' or 'n'.")

def create_election_manifest_interactive() -> Manifest:
    """Create an election manifest interactively with user input."""
    print("\n=== Election Configuration ===")
    
    # Basic election info
    election_title = get_input("Enter election title", "General Election 2023")
    election_scope = get_input("Enter election scope ID", f"election-{uuid.uuid4()}")
    
    # Election dates
    start_date = datetime.now()
    end_date = start_date + timedelta(days=1)
    print(f"Election dates: {start_date} to {end_date}")
    
    # Create geopolitical units
    print("\n=== Geopolitical Units ===")
    geopolitical_units = []
    num_units = get_int_input("Enter number of geopolitical units", 2)
    
    for i in range(num_units):
        print(f"\nGeopolitical Unit {i+1}:")
        unit_id = get_input("  Enter unit ID", f"unit-{i+1}")
        name = get_input("  Enter unit name", f"District {i+1}")
        unit_type = get_input("  Enter unit type (county, state, etc.)", "county")
        
        geopolitical_units.append(
            GeopoliticalUnit(
                object_id=unit_id,
                name=name,
                type=ReportingUnitType.county,
                contact_information=None,
            )
        )
        print(f"Added {name} ({unit_id})")
    
    # Create parties
    print("\n=== Political Parties ===")
    parties = []
    num_parties = get_int_input("Enter number of political parties", 2)
    
    for i in range(num_parties):
        print(f"\nParty {i+1}:")
        party_id = get_input("  Enter party ID", f"party-{i+1}")
        name = get_input("  Enter party name", f"Party {i+1}")
        abbreviation = get_input("  Enter party abbreviation", name[:3].upper())
        
        parties.append(
            Party(
                object_id=party_id,
                name=name,
                abbreviation=abbreviation,
                color=None,
                logo_uri=None,
            )
        )
        print(f"Added {name} ({abbreviation})")
    
    # Create candidates
    print("\n=== Candidates ===")
    candidates = []
    num_candidates = get_int_input("Enter number of candidates", 3)
    
    for i in range(num_candidates):
        print(f"\nCandidate {i+1}:")
        candidate_id = get_input("  Enter candidate ID", f"candidate-{i+1}")
        name = get_input("  Enter candidate name", f"Candidate {i+1}")
        
        # Show available parties
        print("  Available parties:")
        for j, party in enumerate(parties):
            print(f"    {j+1}. {party.name} ({party.abbreviation})")
        
        party_choice = get_int_input("  Select party number", 1)
        if party_choice < 1 or party_choice > len(parties):
            print("Invalid party selection, using first party")
            party_choice = 1
        
        candidates.append(
            Candidate(
                object_id=candidate_id,
                name=name,
                party_id=parties[party_choice-1].object_id,
            )
        )
        print(f"Added {name} ({parties[party_choice-1].abbreviation})")
    
    # Create contests
    print("\n=== Contests ===")
    contests = []
    num_contests = get_int_input("Enter number of contests", 2)
    
    for i in range(num_contests):
        print(f"\nContest {i+1}:")
        contest_id = get_input("  Enter contest ID", f"contest-{i+1}")
        
        # Select geopolitical unit
        print("  Available geopolitical units:")
        for j, unit in enumerate(geopolitical_units):
            print(f"    {j+1}. {unit.name} ({unit.object_id})")
        
        unit_choice = get_int_input("  Select geopolitical unit number", 1)
        if unit_choice < 1 or unit_choice > len(geopolitical_units):
            print("Invalid selection, using first unit")
            unit_choice = 1
        
        name = get_input("  Enter contest name", f"Contest {i+1}")
        votes_allowed = get_int_input("  Enter number of votes allowed", 1)
        number_elected = get_int_input("  Enter number of candidates to be elected", 1)
        
        # Create selections
        selections = []
        print("  Available candidates:")
        for j, candidate in enumerate(candidates):
            party = next((p for p in parties if p.object_id == candidate.party_id), None)
            party_name = f" ({party.abbreviation})" if party else ""
            print(f"    {j+1}. {candidate.name}{party_name}")
        
        num_selections = get_int_input("  How many candidates will be in this contest?", min(3, len(candidates)))
        
        for j in range(num_selections):
            candidate_choice = get_int_input(f"  Select candidate {j+1} (number)", j+1)
            if candidate_choice < 1 or candidate_choice > len(candidates):
                print("Invalid candidate selection, skipped")
                continue
            
            selections.append(
                SelectionDescription(
                    object_id=f"{contest_id}-selection-{j+1}",
                    candidate_id=candidates[candidate_choice-1].object_id,
                    sequence_order=j,
                )
            )
            print(f"  Added {candidates[candidate_choice-1].name}")
        
        contests.append(
            Contest(
                object_id=contest_id,
                sequence_order=i,
                electoral_district_id=geopolitical_units[unit_choice-1].object_id,
                vote_variation=VoteVariationType.one_of_m,
                name=name,
                ballot_selections=selections,
                ballot_title=None,
                ballot_subtitle=None,
                votes_allowed=votes_allowed,
                number_elected=number_elected,
            )
        )
        print(f"Added contest: {name} with {len(selections)} candidates")
    
    # Create ballot styles
    print("\n=== Ballot Styles ===")
    ballot_styles = []
    num_styles = get_int_input("Enter number of ballot styles", 2)
    
    for i in range(num_styles):
        print(f"\nBallot Style {i+1}:")
        style_id = get_input("  Enter ballot style ID", f"style-{i+1}")
        
        # Select geopolitical units
        print("  Available geopolitical units:")
        for j, unit in enumerate(geopolitical_units):
            print(f"    {j+1}. {unit.name} ({unit.object_id})")
        
        selected_units = []
        num_units_in_style = get_int_input("  How many units will be in this ballot style?", 1)
        
        for j in range(num_units_in_style):
            unit_choice = get_int_input(f"  Select unit {j+1} (number)", j+1)
            if unit_choice < 1 or unit_choice > len(geopolitical_units):
                print("Invalid selection, skipped")
                continue
            
            selected_units.append(geopolitical_units[unit_choice-1].object_id)
            print(f"  Added {geopolitical_units[unit_choice-1].name}")
        
        ballot_styles.append(
            BallotStyle(
                object_id=style_id,
                geopolitical_unit_ids=selected_units,
                party_ids=None,
                image_uri=None,
            )
        )
        print(f"Added ballot style {style_id} with {len(selected_units)} units")
    
    # Create the manifest
    manifest = Manifest(
        election_scope_id=election_scope,
        spec_version=SpecVersion.EG0_95,
        type=ElectionType.general,
        start_date=start_date,
        end_date=end_date,
        geopolitical_units=geopolitical_units,
        parties=parties,
        candidates=candidates,
        contests=contests,
        ballot_styles=ballot_styles,
        name=election_title,
        contact_information=None,
    )
    
    print("\n=== Election Summary ===")
    print(f"Title: {manifest.name}")
    print(f"Scope ID: {manifest.election_scope_id}")
    print(f"Dates: {manifest.start_date} to {manifest.end_date}")
    print(f"Geopolitical Units: {len(manifest.geopolitical_units)}")
    print(f"Parties: {len(manifest.parties)}")
    print(f"Candidates: {len(manifest.candidates)}")
    print(f"Contests: {len(manifest.contests)}")
    print(f"Ballot Styles: {len(manifest.ballot_styles)}")
    
    return manifest

def interactive_key_ceremony(number_of_guardians: int, quorum: int) -> Tuple[List[Guardian], Any]:
    """Conduct an interactive key ceremony."""
    print("\n=== Key Ceremony ===")
    
    # Create guardians
    guardians = []
    for i in range(number_of_guardians):
        print(f"\nGuardian {i+1} setup:")
        guardian_id = get_input(f"  Enter ID for guardian {i+1}", str(i+1))
        sequence_order = i + 1
        
        guardian = Guardian.from_nonce(
            guardian_id,
            sequence_order,
            number_of_guardians,
            quorum,
        )
        guardians.append(guardian)
        print(f"✅ Created Guardian {guardian.id}")
    
    # Setup Key Ceremony Mediator
    mediator = KeyCeremonyMediator(
        "key-ceremony-mediator", 
        guardians[0].ceremony_details
    )
    
    # ROUND 1: Public Key Sharing
    print("\n🔹 ROUND 1: Public Key Sharing")
    for guardian in guardians:
        mediator.announce(guardian.share_key())
        print(f"✅ Guardian {guardian.id} announced public key")
    
    # Share Keys
    for guardian in guardians:
        announced_keys = get_optional(mediator.share_announced())
        for key in announced_keys:
            if guardian.id != key.owner_id:
                guardian.save_guardian_key(key)
                print(f"✅ Guardian {guardian.id} saved key from Guardian {key.owner_id}")
    
    # ROUND 2: Partial Key Backup Sharing
    print("\n🔹 ROUND 2: Partial Key Backup Sharing")
    for sending_guardian in guardians:
        print(f"\nGuardian {sending_guardian.id} is generating backups...")
        sending_guardian.generate_election_partial_key_backups()
        
        backups = []
        for designated_guardian in guardians:
            if designated_guardian.id != sending_guardian.id:
                print(f"  Creating backup for Guardian {designated_guardian.id}")
                backup = get_optional(
                    sending_guardian.share_election_partial_key_backup(
                        designated_guardian.id
                    )
                )
                backups.append(backup)
        
        mediator.receive_backups(backups)
        print(f"✅ Mediator received {len(backups)} backups from Guardian {sending_guardian.id}")
    
    # Receive Backups
    for designated_guardian in guardians:
        backups = get_optional(mediator.share_backups(designated_guardian.id))
        print(f"\nGuardian {designated_guardian.id} is receiving backups...")
        
        for backup in backups:
            print(f"  Processing backup from Guardian {backup.owner_id}")
            designated_guardian.save_election_partial_key_backup(backup)
        
        print(f"✅ Guardian {designated_guardian.id} processed {len(backups)} backups")
    
    # ROUND 3: Verification of Backups
    print("\n🔹 ROUND 3: Verification of Backups")
    for designated_guardian in guardians:
        print(f"\nGuardian {designated_guardian.id} is verifying backups...")
        verifications = []
        
        for backup_owner in guardians:
            if designated_guardian.id != backup_owner.id:
                print(f"  Verifying backup from Guardian {backup_owner.id}")
                verification = designated_guardian.verify_election_partial_key_backup(
                    backup_owner.id
                )
                verifications.append(get_optional(verification))
        
        mediator.receive_backup_verifications(verifications)
        print(f"✅ Mediator received {len(verifications)} verifications from Guardian {designated_guardian.id}")
    
    # FINAL: Publish Joint Key
    print("\n🔹 FINAL: Publishing Joint Key")
    joint_key = get_optional(mediator.publish_joint_key())
    print(f"✅ Joint election key published: {joint_key.joint_public_key}")
    
    return guardians, joint_key

def interactive_voting(manifest: Manifest, context: CiphertextElectionContext) -> Tuple[List[PlaintextBallot], List[CiphertextBallot]]:
    """Conduct interactive voting."""
    print("\n=== Voting Process ===")
    
    # Create encryption device and mediator
    device = EncryptionDevice(device_id=1, session_id=1, launch_code=1, location="polling-place")
    internal_manifest = InternalManifest(manifest)
    encrypter = EncryptionMediator(internal_manifest, context, device)
    
    # Get number of voters
    num_voters = get_int_input("Enter number of voters", 5)
    
    plaintext_ballots = []
    ciphertext_ballots = []
    
    for i in range(num_voters):
        print(f"\n=== Voter {i+1} ===")
        
        # Select ballot style
        print("Available ballot styles:")
        for j, style in enumerate(manifest.ballot_styles):
            print(f"  {j+1}. {style.object_id} (Units: {', '.join(style.geopolitical_unit_ids)})")
        
        style_choice = get_int_input("Select ballot style", 1)
        if style_choice < 1 or style_choice > len(manifest.ballot_styles):
            print("Invalid selection, using first style")
            style_choice = 1
        
        ballot_style = manifest.ballot_styles[style_choice-1]
        geo_unit_ids = ballot_style.geopolitical_unit_ids
        
        # Find contests for this ballot style
        available_contests = [
            contest for contest in manifest.contests 
            if contest.electoral_district_id in geo_unit_ids
        ]
        
        ballot_contests = []
        
        for contest in available_contests:
            print(f"\nContest: {contest.name}")
            print(f"Vote for {contest.number_elected} of {len(contest.ballot_selections)} candidates")
            
            # Show candidates
            selections = []
            for j, selection in enumerate(contest.ballot_selections):
                candidate = next((c for c in manifest.candidates if c.object_id == selection.candidate_id), None)
                party = next((p for p in manifest.parties if candidate and p.object_id == candidate.party_id), None)
                party_name = f" ({party.name})" if party else ""
                print(f"  {j+1}. {candidate.name if candidate else 'Unknown'}{party_name}")
            
            # Get votes
            votes = []
            for _ in range(contest.number_elected):
                choice = get_int_input("  Enter your choice (number)", 1)
                if choice < 1 or choice > len(contest.ballot_selections):
                    print("Invalid choice, skipped")
                    continue
                votes.append(choice-1)
            
            # Create selections
            ballot_selections = []
            for j, selection in enumerate(contest.ballot_selections):
                vote = 1 if j in votes else 0
                ballot_selections.append(
                    PlaintextBallotSelection(
                        object_id=selection.object_id,
                        vote=vote,
                        is_placeholder_selection=False,
                    )
                )
            
            ballot_contests.append(
                PlaintextBallotContest(
                    object_id=contest.object_id,
                    ballot_selections=ballot_selections
                )
            )
        
        # Create and encrypt ballot
        plaintext_ballot = PlaintextBallot(
            object_id=f"ballot-{i+1}",
            style_id=ballot_style.object_id,
            contests=ballot_contests,
        )
        
        encrypted_ballot = encrypter.encrypt(plaintext_ballot)
        if encrypted_ballot:
            ciphertext_ballot = get_optional(encrypted_ballot)
            plaintext_ballots.append(plaintext_ballot)
            ciphertext_ballots.append(ciphertext_ballot)
            print(f"✅ Ballot encrypted and submitted")
        else:
            print("❌ Failed to encrypt ballot")
    
    return plaintext_ballots, ciphertext_ballots

def interactive_decryption(guardians: List[Guardian], manifest: Manifest, context: CiphertextElectionContext, ciphertext_tally: CiphertextTally) -> PlaintextTally:
    """Conduct interactive decryption."""
    print("\n=== Decryption Process ===")
    
    # Setup decryption mediator
    decryption_mediator = DecryptionMediator(
        "decryption-mediator",
        context,
    )
    
    # Collect decryption shares from guardians
    available_guardians = guardians.copy()
    while True:
        print("\nAvailable guardians:")
        for i, guardian in enumerate(available_guardians):
            print(f"  {i+1}. {guardian.id}")
        
        print("\nOptions:")
        print("  1. Add guardian decryption share")
        print("  2. Complete decryption")
        
        choice = get_int_input("Select option", 1)
        
        if choice == 1:
            # Add guardian share
            guardian_choice = get_int_input("Select guardian to add share", 1)
            if guardian_choice < 1 or guardian_choice > len(available_guardians):
                print("Invalid selection")
                continue
            
            guardian = available_guardians[guardian_choice-1]
            
            # Guardian computes their share
            guardian_key = guardian.share_key()
            tally_share = guardian.compute_tally_share(ciphertext_tally, context)
            
            # Add to mediator
            decryption_mediator.announce(
                guardian_key, 
                get_optional(tally_share),
                []  # No ballot shares in this simplified version
            )
            
            print(f"✅ Guardian {guardian.id} added decryption share")
            available_guardians.pop(guardian_choice-1)
        
        elif choice == 2:
            # Complete decryption
            if len(decryption_mediator.get_available_guardians()) < context.quorum:
                print(f"❌ Need at least {context.quorum} guardians for decryption")
                continue
            
            # Get Lagrange coefficients
            lagrange_coefficients = LagrangeCoefficientsRecord(
                decryption_mediator.get_lagrange_coefficients()
            )
            
            # Decrypt the tally
            plaintext_tally = get_optional(
                decryption_mediator.get_plaintext_tally(ciphertext_tally, manifest)
            )
            
            if plaintext_tally:
                print("✅ Successfully decrypted tally")
                return plaintext_tally
            else:
                print("❌ Failed to decrypt tally")
                continue
        
        else:
            print("Invalid choice")

def run_interactive_election():
    """Run an interactive election demo."""
    print("""
    ====================================
    ELECTIONGUARD INTERACTIVE DEMO
    ====================================
    """)
    
    # Step 1: Configure Election
    print("\n=== STEP 1: Configure Election ===")
    manifest = create_election_manifest_interactive()
    
    # Get guardian parameters
    number_of_guardians = get_int_input("\nEnter number of guardians", 3)
    quorum = get_int_input("Enter quorum required for decryption", 2)
    if quorum > number_of_guardians:
        print("Quorum cannot exceed number of guardians, setting to number of guardians")
        quorum = number_of_guardians
    
    # Step 2: Key Ceremony
    print("\n=== STEP 2: Key Ceremony ===")
    guardians, joint_key = interactive_key_ceremony(number_of_guardians, quorum)
    
    # Build election context
    election_builder = ElectionBuilder(
        number_of_guardians, 
        quorum,
        manifest
    )
    election_builder.set_public_key(joint_key.joint_public_key)
    election_builder.set_commitment_hash(joint_key.commitment_hash)
    internal_manifest, context = get_optional(election_builder.build())
    
    # Step 3: Voting
    print("\n=== STEP 3: Voting ===")
    plaintext_ballots, ciphertext_ballots = interactive_voting(manifest, context)
    
    # Step 4: Tallying
    print("\n=== STEP 4: Tallying ===")
    ballot_store = DataStore()
    ballot_box = BallotBox(internal_manifest, context, ballot_store)
    
    # Cast all ballots
    for ballot in ciphertext_ballots:
        submitted_ballot = ballot_box.cast(ballot)
        if submitted_ballot:
            print(f"✅ Cast ballot: {ballot.object_id}")
        else:
            print(f"❌ Failed to cast ballot: {ballot.object_id}")
    
    # Tally the ballots
    ciphertext_tally = get_optional(
        tally_ballots(ballot_store, internal_manifest, context)
    )
    print(f"\n✅ Created encrypted tally with {ciphertext_tally.cast()} cast ballots")
    
    # Step 5: Decryption
    print("\n=== STEP 5: Decryption ===")
    plaintext_tally = interactive_decryption(guardians, manifest, context, ciphertext_tally)
    
    # Step 6: Results
    print("\n=== ELECTION RESULTS ===")
    print("\nContest Results:")
    for contest in manifest.contests:
        print(f"\nContest: {contest.name}")
        contest_results = plaintext_tally.contests.get(contest.object_id)
        
        if contest_results:
            for selection in contest.ballot_selections:
                candidate = next((c for c in manifest.candidates if c.object_id == selection.candidate_id), None)
                party = next((p for p in manifest.parties if candidate and p.object_id == candidate.party_id), None)
                party_name = f" ({party.name})" if party else ""
                
                vote_count = contest_results.selections[selection.object_id].tally
                print(f"  {candidate.name if candidate else 'Unknown'}{party_name}: {vote_count} votes")
        else:
            print("  No results available")
    
    print("\n=== ELECTION COMPLETE ===")

if __name__ == "__main__":
    run_interactive_election()