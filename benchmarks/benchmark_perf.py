"""Quick benchmark to verify performance after logging fix."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import json
from services.setup_guardians import setup_guardians_service
from services.create_encrypted_ballot import create_encrypted_ballot_service, create_election_manifest, create_plaintext_ballot
from services.create_encrypted_tally import create_encrypted_tally_service
from services.create_partial_decryption import create_partial_decryption_service

PARTY_NAMES = ['Alice', 'Bob', 'Carol', 'David']
CANDIDATE_NAMES = ['Alice Johnson', 'Bob Smith', 'Carol Williams', 'David Brown']
N_GUARDIANS = 3
QUORUM = 2
N_BALLOTS = 10

from electionguard.serialize import to_raw
from electionguard.hash import hash_elems

def generate_ballot_hash_electionguard(ballot) -> str:
    """Same as in api.py."""
    if hasattr(ballot, 'object_id') and hasattr(ballot, 'crypto_hash'):
        return ballot.crypto_hash.to_hex()
    serialized = to_raw(ballot)
    return hash_elems(serialized).to_hex()

print(f"\n=== Performance Benchmark (after logging fix) ===\n")

# 1. Setup
t = time.time()
setup = setup_guardians_service(N_GUARDIANS, QUORUM, PARTY_NAMES, CANDIDATE_NAMES)
elapsed = (time.time() - t) * 1000
print(f"setup_guardians:            {elapsed:6.0f}ms  {'OK' if elapsed < 500 else 'SLOW'}")

joint_key = setup['joint_public_key']
commitment_hash = setup['commitment_hash']
guardians = setup['guardians']

# 2. Encrypt ballots
encrypted_ballots = []
ballot_times = []
for i in range(N_BALLOTS):
    vote_for = CANDIDATE_NAMES[i % len(CANDIDATE_NAMES)]
    ballot_id = f'ballot-{i+1}'
    t = time.time()
    enc = create_encrypted_ballot_service(
        PARTY_NAMES, CANDIDATE_NAMES, vote_for, ballot_id,
        joint_key, commitment_hash, N_GUARDIANS, QUORUM,
        create_plaintext_ballot, create_election_manifest, generate_ballot_hash_electionguard
    )
    ballot_times.append((time.time() - t) * 1000)
    encrypted_ballots.append(enc)

avg_ballot = sum(ballot_times) / len(ballot_times)
max_ballot = max(ballot_times)
print(f"encrypt_ballot avg:         {avg_ballot:6.0f}ms  {'OK' if avg_ballot < 500 else 'SLOW'}  (max {max_ballot:.0f}ms)")

# 3. Tally
t = time.time()
tally_result = create_encrypted_tally_service(encrypted_ballots, PARTY_NAMES, CANDIDATE_NAMES)
elapsed = (time.time() - t) * 1000
print(f"create_tally ({N_BALLOTS} ballots):   {elapsed:6.0f}ms  {'OK' if elapsed < 500 else 'SLOW'}")
tally_json = tally_result['tally']

# 4. Partial decryption for all guardians
partial_decryptions = []
for idx, g in enumerate(guardians):
    t = time.time()
    pd = create_partial_decryption_service(
        g['guardian_data'], g['private_key'], tally_json, PARTY_NAMES, CANDIDATE_NAMES
    )
    elapsed = (time.time() - t) * 1000
    print(f"partial_decrypt  [g{idx+1}]:       {elapsed:6.0f}ms  {'OK' if elapsed < 500 else 'SLOW'}")
    partial_decryptions.append(pd)

print(f"\nAll checks complete. Got {len(partial_decryptions)} partial decryption sets.")
print("Done.")
