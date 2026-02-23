"""Profile partial decryption to find the 900ms bottleneck."""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.setup_guardians import setup_guardians_service
from services.create_encrypted_ballot import create_election_manifest, create_encrypted_ballot_service
from services.create_encrypted_tally import raw_to_ciphertext_tally, create_encrypted_tally_service
from manifest_cache import get_manifest_cache
from electionguard.group import int_to_q, int_to_p
from electionguard.key_ceremony import ElectionKeyPair
from electionguard.elgamal import ElGamalKeyPair
from electionguard.election_polynomial import ElectionPolynomial
from electionguard.serialize import from_raw
from binary_serialize import from_binary_transport, to_binary_transport
from electionguard.decryption import compute_decryption_share
from electionguard.ballot import SubmittedBallot

PARTY_NAMES = ['Democratic Alliance', 'Progressive Coalition', 'Unity Party', 'Reform League']
CANDIDATE_NAMES = ['Alice Johnson', 'Bob Smith', 'Carol Williams', 'David Brown']
N_GUARDIANS = 3
QUORUM = 2
N_BALLOTS = 10

print(f"Setting up {N_GUARDIANS} guardians...")
gr = setup_guardians_service(N_GUARDIANS, QUORUM, PARTY_NAMES, CANDIDATE_NAMES)

print(f"Encrypting {N_BALLOTS} ballots...")
selections = [
    {'Alice Johnson': True, 'Bob Smith': False, 'Carol Williams': False, 'David Brown': False},
    {'Alice Johnson': False, 'Bob Smith': True, 'Carol Williams': False, 'David Brown': False},
    {'Alice Johnson': False, 'Bob Smith': False, 'Carol Williams': True, 'David Brown': False},
]

ballot_list = []
for i in range(N_BALLOTS):
    br = create_encrypted_ballot_service(
        PARTY_NAMES, CANDIDATE_NAMES,
        gr['joint_public_key'], gr['commitment_hash'],
        N_GUARDIANS, QUORUM,
        f'ballot-{i+1}',
        selections[i % len(selections)],
        create_election_manifest, None, None
    )
    ballot_list.append(br['encrypted_ballot'])

print(f"Creating tally...")
tr = create_encrypted_tally_service(
    PARTY_NAMES, CANDIDATE_NAMES,
    gr['joint_public_key'], gr['commitment_hash'],
    N_GUARDIANS, QUORUM,
    ballot_list, create_election_manifest, raw_to_ciphertext_tally
)

print(f"\n--- PROFILING PARTIAL DECRYPTION ---")
guardian_data = gr['guardian_data'][0]
private_key = gr['private_keys'][0]

# Build key pair  
pk_data = private_key['private_key']
private_key_value = int_to_q(int(pk_data['key']))
pub_data = private_key['public_key']
public_key_value = int_to_p(int(pub_data['public_key']))
poly_data = private_key['polynomial']

t = time.perf_counter()
polynomial_obj = from_raw(ElectionPolynomial, json.dumps(poly_data))
print(f"  polynomial deserialization: {(time.perf_counter()-t)*1000:.1f}ms")

election_key = ElectionKeyPair(
    owner_id=guardian_data['id'],
    sequence_order=guardian_data['sequence_order'],
    key_pair=ElGamalKeyPair(private_key_value, public_key_value),
    polynomial=polynomial_obj
)

t = time.perf_counter()
cache = get_manifest_cache()
internal_manifest, context = cache.get_or_create_context(
    PARTY_NAMES, CANDIDATE_NAMES,
    gr['joint_public_key'], gr['commitment_hash'],
    N_GUARDIANS, QUORUM, create_election_manifest
)
manifest = cache.get_or_create_manifest(PARTY_NAMES, CANDIDATE_NAMES, create_election_manifest)
print(f"  context/manifest from cache: {(time.perf_counter()-t)*1000:.1f}ms")

t = time.perf_counter()
ciphertext_tally = raw_to_ciphertext_tally(tr['ciphertext_tally'], manifest=manifest)
print(f"  tally deserialization: {(time.perf_counter()-t)*1000:.1f}ms")

t = time.perf_counter()
submitted_ballots = []
for ballot_json in tr['submitted_ballots_json'] if 'submitted_ballots_json' in tr else ballot_list:
    if isinstance(ballot_json, dict):
        submitted_ballots.append(from_raw(SubmittedBallot, json.dumps(ballot_json)))
    else:
        submitted_ballots.append(from_binary_transport(SubmittedBallot, ballot_json))
print(f"  ballot ({len(submitted_ballots)}) deserialization: {(time.perf_counter()-t)*1000:.1f}ms")

# How many contests and selections in the tally?
print(f"\n  Tally structure:")
for cid, contest in ciphertext_tally.contests.items():
    print(f"    Contest {cid}: {len(contest.selections)} selections")

t = time.perf_counter()
tally_share = compute_decryption_share(election_key, ciphertext_tally, context)
print(f"\n  compute_decryption_share: {(time.perf_counter()-t)*1000:.1f}ms")

t = time.perf_counter()
ser = to_binary_transport(tally_share)
print(f"  serialize tally_share: {(time.perf_counter()-t)*1000:.1f}ms")

print(f"\nDone!")
