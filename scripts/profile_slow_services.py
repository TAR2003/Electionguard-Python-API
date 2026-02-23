"""Profile slow services directly."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cProfile, pstats, io, time, logging, json
logging.getLogger("electionguard").setLevel(logging.WARNING)
logging.getLogger().setLevel(logging.WARNING)

from services.setup_guardians import setup_guardians_service
from services.create_encrypted_ballot import create_encrypted_ballot_service, create_election_manifest
from services.create_encrypted_tally import create_encrypted_tally_service, ciphertext_tally_to_raw, raw_to_ciphertext_tally
from services.create_partial_decryption import create_partial_decryption_service
from services.create_partial_decryption_shares import compute_ballot_shares

logging.getLogger("electionguard").setLevel(logging.WARNING)

PARTY_NAMES = ["PartyA", "PartyB"]
CANDIDATE_NAMES = ["Alice", "Bob", "Carol", "David"]
N_GUARDIANS = 3
QUORUM = 2
N_BALLOTS = 10

print("=== Setup guardians ===")
t = time.time()
res = setup_guardians_service(N_GUARDIANS, QUORUM, PARTY_NAMES, CANDIDATE_NAMES)
print(f"  {(time.time()-t)*1000:.0f}ms")
jpk = res["joint_public_key"]
chash = res["commitment_hash"]
guardians = res["guardians"]

from electionguard.serialize import to_raw, from_raw
from electionguard.group import int_to_p, int_to_q
from electionguard_tools.helpers.election_builder import ElectionBuilder

manifest = create_election_manifest(PARTY_NAMES, CANDIDATE_NAMES)
builder = ElectionBuilder(N_GUARDIANS, QUORUM, manifest)
builder.set_public_key(int_to_p(int(jpk)))
builder.set_commitment_hash(int_to_q(int(chash)))
_, _ = builder.build()
manifest_raw = to_raw(manifest)

from electionguard_tools.helpers.election_builder import ElectionBuilder as EB2
b2 = EB2(N_GUARDIANS, QUORUM, manifest)
b2.set_public_key(int_to_p(int(jpk)))
b2.set_commitment_hash(int_to_q(int(chash)))
_, ctx = b2.build()
context_raw = to_raw(ctx)

print("=== Encrypt 10 ballots ===")
ballots = []
for i in range(N_BALLOTS):
    r = create_encrypted_ballot_service(
        f"ballot-{i+1}", "style-1",
        [{"contest_id": "contest-0", "selections": [
            {"selection_id": "sel-0-0", "vote": 1 if i % 4 == 0 else 0},
            {"selection_id": "sel-0-1", "vote": 1 if i % 4 == 1 else 0},
            {"selection_id": "sel-0-2", "vote": 1 if i % 4 == 2 else 0},
            {"selection_id": "sel-0-3", "vote": 1 if i % 4 == 3 else 0},
        ]}],
        manifest_raw, context_raw, jpk, chash
    )
    ballots.append(r["encrypted_ballot"])
print(f"  Done - {N_BALLOTS} ballots")

print("\n=== Profile create_encrypted_tally ===")
pr = cProfile.Profile()
pr.enable()
t = time.time()
tally_res = create_encrypted_tally_service(
    PARTY_NAMES, CANDIDATE_NAMES, jpk, chash,
    ballots, N_GUARDIANS, QUORUM,
    create_election_manifest, ciphertext_tally_to_raw
)
elapsed = (time.time()-t)*1000
pr.disable()
print(f"  TOTAL: {elapsed:.0f}ms")
s = io.StringIO()
pstats.Stats(pr, stream=s).sort_stats("cumulative").print_stats(25)
print(s.getvalue())

print("\n=== Profile create_partial_decryption (guardian 1) ===")
g1 = guardians[0]
pr2 = cProfile.Profile()
pr2.enable()
t = time.time()
pd_res = create_partial_decryption_service(
    PARTY_NAMES, CANDIDATE_NAMES,
    g1["guardian_id"], g1["guardian_data"], g1["private_key"],
    g1["public_key"], None,
    tally_res["ciphertext_tally"], tally_res["submitted_ballots"],
    jpk, chash, N_GUARDIANS, QUORUM,
    create_election_manifest, raw_to_ciphertext_tally, compute_ballot_shares
)
elapsed2 = (time.time()-t)*1000
pr2.disable()
print(f"  TOTAL: {elapsed2:.0f}ms")
s2 = io.StringIO()
pstats.Stats(pr2, stream=s2).sort_stats("cumulative").print_stats(25)
print(s2.getvalue())
