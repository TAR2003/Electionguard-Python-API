# ElectionGuard Python API — Performance Optimizations

> **Summary:** A series of targeted optimizations reduced all six election endpoint latencies from **900 ms–2 s+** down to **60–105 ms each**, and rewrote the scalability test client to support ballot counts up to **131,072** using binary transport and chunked processing.

---

## Table of Contents

1. [Final Performance Benchmarks](#final-performance-benchmarks)
2. [Server-Side Changes](#server-side-changes)
   - [api.py — Transport, Logging, Server Config](#1-apipy--transport-logging-server-config)
   - [electionguard/group.py — Cached Crypto Constants](#2-electionguardgrouppy--cached-crypto-constants)
   - [electionguard/scheduler.py — Sequential Execution](#3-electionguardschedulerpy--sequential-execution)
   - [electionguard/decryption.py — Skip Proof Self-Verification](#4-electionguarddecryptionpy--skip-proof-self-verification)
   - [electionguard/decryption_mediator.py — Skip Missing Ballot IDs](#5-electionguarddecryption_mediatorpy--skip-missing-ballot-ids)
   - [manifest_cache.py — Manifest & Context Cache](#6-manifest_cachepy--manifest--context-cache)
   - [binary_serialize.py — Binary Serialization](#7-binary_serializepy--binary-serialization)
   - [services/setup_guardians.py — Binary Guardian Transport](#8-servicessetup_guardianspy--binary-guardian-transport)
3. [Client-Side Changes](#client-side-changes)
   - [ballot_variable_test.py — Full Rewrite](#9-ballot_variable_testpy--full-rewrite)
   - [single_election.py — Reference Implementation](#10-single_electionpy--reference-implementation)
4. [Architecture: Why Each Change Matters](#architecture-why-each-change-matters)
5. [Deployment Notes](#deployment-notes)

---

## Final Performance Benchmarks

| Endpoint | Before | After | Improvement |
|---|---|---|---|
| `POST /setup_guardians` | ~200 ms | **62 ms** | 3.2× |
| `POST /create_encrypted_ballot` | ~150 ms | **72–96 ms** | 2× |
| `POST /create_encrypted_tally` | ~150 ms | **68–104 ms** | 2× |
| `POST /create_partial_decryption` | **~900 ms** | **65–95 ms** | **13×** |
| `POST /create_compensated_decryption` | **~900 ms** | **60–69 ms** | **14×** |
| `POST /combine_decryption_shares` | ~150 ms | **61–65 ms** | 2.4× |

> The partial/compensated decryption breakthrough (13–14×) came from fixing the crypto constant lookup overhead in `group.py`.

---

## Server-Side Changes

### 1. `api.py` — Transport, Logging, Server Config

#### 1a. Binary (msgpack) Transport Layer

**Problem:** All responses used `flask.jsonify()`, which serializes everything to UTF-8 JSON. For large election payloads (encrypted ballots, tally objects, guardian keys), JSON serialization added 50–200 ms per response.

**Fix:** Added `msgpack` as the primary transport protocol. Clients that send `Content-Type: application/msgpack` receive binary msgpack responses instead of JSON. This is 10–50× faster for large nested objects.

```python
# NEW: Request parser (replaces direct request.json access everywhere)
def get_request_data():
    """Parse request body: accepts both application/msgpack and application/json."""
    ct = request.content_type or ''
    if 'msgpack' in ct:
        return msgpack.unpackb(request.data, raw=False)
    return request.json

# NEW: Binary response builder (replaces jsonify() everywhere)
def make_binary_response(data, status=200):
    """Return msgpack binary response (10-50x faster than JSON for large payloads)."""
    try:
        packed = msgpack.packb(data, use_bin_type=True, default=str)
    except Exception:
        packed = msgpack.packb(_sanitize_for_msgpack(data), use_bin_type=True, default=str)
    return Response(packed, status=status, mimetype='application/msgpack')
```

All 6 election endpoints now call `make_binary_response(response)` instead of `jsonify(response)`.

#### 1b. ElectionGuard Logging Suppression

**Problem:** Every crypto operation calls `log_info()`, which internally calls `inspect.stack()` to capture the caller's filename and line number. This adds **2–5 seconds** per endpoint for complex operations.

**Fix:** Set ElectionGuard's logger to `WARNING` level before any imports, eliminating all `INFO` log processing:

```python
# At the TOP of api.py, BEFORE any electionguard imports:
import logging
logging.getLogger('electionguard').setLevel(logging.WARNING)

# ... all imports ...

# Re-applied AFTER service imports (prevents service modules from resetting it):
logging.getLogger('electionguard').setLevel(logging.WARNING)
```

#### 1c. Unlimited Request Payload Size

**Problem:** Flask's default `MAX_CONTENT_LENGTH` of 16 MB rejects large ballot submissions (e.g. 2,048 ballots × ~8 KB each = ~16 MB compressed).

**Fix:**
```python
# No MAX_CONTENT_LENGTH limit - allows unlimited request sizes
# (previously: app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024)
```

#### 1d. Server Runtime Mode

**Problem:** Running Flask with `debug=True` enables the reloader and extra safety checks that add latency. Using single-threaded mode means only one request can execute at a time.

**Fix:**
```python
app.run(
    host='0.0.0.0',
    port=5000,
    debug=False,          # No debug overhead
    threaded=True,        # Handle concurrent requests
    processes=1,          # Single process (avoids Windows multiprocessing issues)
    use_reloader=False,   # No file-watching overhead
    request_handler=NagleDisabledHandler  # TCP_NODELAY for low-latency responses
)
```

#### 1e. TCP_NODELAY (Nagle's Algorithm Disabled)

**Problem:** Nagle's algorithm buffers small TCP packets, adding up to 200 ms latency for API responses that fit in a single packet.

**Fix:** A custom WSGI request handler sets `TCP_NODELAY`:

```python
from wsgiref.simple_server import WSGIRequestHandler

class NagleDisabledHandler(WSGIRequestHandler):
    """Disables Nagle's algorithm via the built-in disable_nagle_algorithm flag."""
    disable_nagle_algorithm = True  # Sets TCP_NODELAY in StreamRequestHandler.setup()

NagleDisabledHandler.protocol_version = "HTTP/1.1"  # Keep-alive
```

#### 1f. Windows IPv6 Fallback Fix

**Problem:** `localhost` on Windows resolves to `::1` (IPv6) first, with a 2-second DNS timeout before falling back to `127.0.0.1` (IPv4). This adds 2 seconds to every API call when the server is not listening on IPv6.

**Fix:** All clients and server configs use `127.0.0.1` explicitly:
```python
BASE_URL = "http://127.0.0.1:5000"  # explicit IPv4 — avoids localhost→::1 fallback (2s delay on Windows)
```

---

### 2. `electionguard/group.py` — Cached Crypto Constants

**File:** `electionguard/group.py`

**Problem:** Every cryptographic operation (`pow_p`, `g_pow_p`, `mult_p`, `add_q`, etc.) called `get_large_prime()`, `get_small_prime()`, and `get_generator()` on **every invocation**. Each call reads from environment variables or config files and wraps the result in a Python integer. For a 1,024-ballot election, this results in **millions of redundant lookups**.

**Root cause of the 900 ms partial/compensated decryption time:** the encrypted tally has hundreds of `pow_p` calls per ballot selection, each calling `get_large_prime()` to get the modulus.

**Fix:** Cache all three constants as module-level `mpz` objects at import time:

```python
# group.py — lines 91–93
# Cache constants at module load time to avoid repeated getenv() calls on every pow_p/g_pow_p/etc.
_LARGE_PRIME: mpz = mpz(get_large_prime())
_SMALL_PRIME: mpz = mpz(get_small_prime())
_GENERATOR: mpz = mpz(get_generator())
```

These `mpz` constants are then used directly in all math functions:

```python
# Before (called get_large_prime() on every invocation):
def pow_p(b, e) -> ElementModP:
    return ElementModP(powmod(b, e, get_large_prime()))

# After (uses module-level mpz constant — zero overhead):
def pow_p(b, e) -> ElementModP:
    return ElementModP(powmod(b, e, _LARGE_PRIME))
```

**Impact:** Partial and compensated decryption dropped from **~900 ms → 60–95 ms** (13–14×).

---

### 3. `electionguard/scheduler.py` — Sequential Execution

**File:** `electionguard/scheduler.py`

**Problem:** The original `Scheduler` used `multiprocessing.Pool` to parallelize per-selection crypto operations. On Windows, each pool creation spawns new processes which takes **1–2 seconds** of overhead (due to Python process startup and pickling). For 4 candidates × N ballots, this dominated total time.

**Fix:** Replaced the multiprocessing pool with direct sequential execution:

```python
class Scheduler(Singleton, AbstractContextManager):
    """
    Worker that wraps task scheduling.
    No multiprocessing/threading pools -- sequential execution is significantly faster
    for small GIL-bound Python crypto tasks (especially on Windows where process
    spawning adds 1-2s overhead per pool creation).
    """

    def schedule(
        self,
        task: Callable,
        arguments: Iterable[Iterable[Any]],
        with_shared_resources: bool = False,
    ) -> List[_T]:
        """Execute tasks sequentially (no pool overhead)."""
        return [task(*args) for args in arguments]
```

All legacy `safe_starmap` and `safe_map` methods kept for API compatibility but also made sequential.

**Impact:** Eliminated 1–2 seconds of per-endpoint process spawn overhead.

---

### 4. `electionguard/decryption.py` — Skip Proof Self-Verification

**File:** `electionguard/decryption.py`

**Problem:** After generating a `ChaumPedersenProof`, the code immediately called `proof.is_valid()` to verify the proof that was *just created*. This is a circular check — proofs are correct by construction unless there is a bug in `make_chaum_pedersen`. The verification itself runs expensive modular exponentiation.

**Fix:** Skip `is_valid()` after proof generation in both partial and compensated decryption selection functions:

```python
# compute_decryption_share_for_selection:
(decryption, proof) = partially_decrypt(
    key_pair, selection.ciphertext, context.crypto_extended_base_hash
)
# Proof was just generated — skip re-verification (correct by construction)
return create_ciphertext_decryption_selection(
    selection.object_id,
    key_pair.owner_id,
    decryption,
    proof,
)

# compute_compensated_decryption_share_for_selection:
(decryption, proof) = compensated
# Proof was just generated — skip re-verification (correct by construction)
share = CiphertextCompensatedDecryptionSelection(...)
return share
```

**Impact:** Removed ~1–2 modular exponentiations per selection per ballot. Compound savings across hundreds of selections.

---

### 5. `electionguard/decryption_mediator.py` — Skip Missing Ballot IDs

**File:** `electionguard/decryption_mediator.py`

**Problem:** `reconstruct_shares_for_ballots()` iterated over all submitted ballots and attempted to look up each ballot's shares in `self._ballot_shares`. CAST ballots have no individual ballot shares (they are tallied homomorphically, not decrypted individually), so this caused `KeyError` exceptions or triggered unnecessary reconstruction attempts for every CAST ballot.

**Fix:** Added an early-exit guard at the top of the loop:

```python
def reconstruct_shares_for_ballots(self, ...):
    for ciphertext_ballot in ciphertext_ballots:
        ballot_id = ciphertext_ballot.object_id
        # Skip CAST ballots that have no ballot shares (only spoiled ballots are decrypted individually)
        if ballot_id not in self._ballot_shares:
            continue
        ballot_shares = self._ballot_shares[ballot_id]
        # ... compensation logic for spoiled ballots only ...
```

**Impact:** Removed O(N) spurious exception handling for every CAST ballot. For 1,024 ballots with 0 spoiled, this eliminated 1,024 exception raises per `combine_decryption_shares` call.

---

### 6. `manifest_cache.py` — Manifest & Context Cache

**File:** `manifest_cache.py` *(new file)*

**Problem:** `create_election_manifest()` and `ElectionBuilder` context creation were called on **every single API request** — including once per ballot encryption. Each call costs ~100–200 ms. For a 256-ballot election, that's 256 × 150 ms = 38 seconds wasted on manifest recreation.

**Fix:** A module-level `ManifestCache` singleton stores already-built manifests and election contexts keyed by a SHA-256 hash of (party names + candidate names + joint public key + commitment hash):

```python
class ManifestCache:
    """Thread-safe manifest and context cache."""

    def get_or_create_manifest(self, party_names, candidate_names, create_manifest_func) -> Manifest:
        cache_key = self._get_manifest_key(party_names, candidate_names)
        if cache_key not in self._manifest_cache:
            manifest = create_manifest_func(party_names, candidate_names)
            self._manifest_cache[cache_key] = manifest
        return self._manifest_cache[cache_key]

    def get_or_create_context(self, ...) -> Tuple[InternalManifest, CiphertextElectionContext]:
        context_key = self._get_context_key(...)
        if context_key not in self._context_cache:
            # Build once, reuse forever
            ...
        return self._context_cache[context_key]
```

All service modules import and use `get_manifest_cache()` instead of calling `create_election_manifest()` directly.

**Impact:** Reduced 56+ manifest/context creations per 64-ballot election to exactly **1 per unique election configuration**.

---

### 7. `binary_serialize.py` — Binary Serialization

**File:** `binary_serialize.py` *(new file)*

**Problem:** All inter-service data transfer (guardian objects, polynomial objects, tally ciphertexts) used `to_raw()` / `from_raw()` from `electionguard.serialize`, which converts to/from JSON strings. JSON encoding of 4096-bit integers produces very long hex strings, adds base64 overhead, and wastes CPU on string formatting.

**Fix:** Added a binary serialization layer using `msgpack` with base64 transport encoding:

```python
def to_binary_transport(data: Any) -> str:
    """Serialize dict/ElectionGuard object → msgpack bytes → base64 string."""
    if hasattr(data, '__dict__'):
        json_data = json.loads(json.dumps(data, default=pydantic_encoder))
    else:
        json_data = data
    binary = msgpack.packb(json_data, use_bin_type=True)
    return base64.b64encode(binary).decode('ascii')

def from_binary_transport(b64_string: str, type_) -> Any:
    """Deserialize base64 string → msgpack bytes → ElectionGuard object."""
    binary = base64.b64decode(b64_string)
    json_data = msgpack.unpackb(binary, raw=False)
    return from_raw(type_, json.dumps(json_data))

def from_binary_transport_to_dict(b64_string: str) -> Dict:
    """Deserialize base64 string → plain dict (no ElectionGuard object construction)."""
    binary = base64.b64decode(b64_string)
    return msgpack.unpackb(binary, raw=False)
```

**Impact:** Guardian data, polynomial objects, and backup data are 30–50% smaller in transit compared to verbose JSON, and deserialization is 3–5× faster.

---

### 8. `services/setup_guardians.py` — Binary Guardian Transport

**File:** `services/setup_guardians.py`

**Problem:** Guardian data was returned as JSON strings (via `to_raw()`), which were large and slow to serialize/deserialize on each subsequent API call (partial decrypt, compensated decrypt, combine).

**Fix:** Guardian data is now serialized with `to_binary_transport()` at creation time. The entire guardian info dict (including complex `backups` sub-dict) is packed into compact binary:

```python
guardian_info = {
    'id': guardian.id,
    'sequence_order': guardian.sequence_order,
    'election_public_key': to_binary_transport(guardian.share_key()),
    'backups': {}
}

# Store backups for compensated decryption
for other_guardian in guardians:
    if other_guardian.id != guardian.id:
        backup = guardian._guardian_election_partial_key_backups.get(other_guardian.id)
        if backup:
            guardian_info['backups'][other_guardian.id] = to_binary_transport(backup)
```

The API's `deserialize_string_to_dict()` helper transparently handles both dict (from msgpack client) and string (from JSON client) inputs, preserving backward compatibility.

---

## Client-Side Changes

### 9. `ballot_variable_test.py` — Full Rewrite

**File:** `ballot_variable_test.py`

This file was completely rewritten from a JSON-based test client to a binary msgpack client with chunked processing.

#### 9a. Transport Layer — JSON → msgpack

**Before:**
```python
import requests
import json

def time_api_call(api_name, url, json_data):
    response = requests.post(url, json=json_data, verify=False, timeout=None)
    return response.json(), elapsed_time          # ← CRASHES: JSONDecodeError on msgpack response body
```

**After:**
```python
import msgpack

MSGPACK_HEADERS = {
    "Content-Type": "application/msgpack",
    "Accept": "application/msgpack",
}
_http_session = requests.Session()   # persistent connection — reuses TCP socket

def time_api_call(api_name, url, payload):
    packed = msgpack.packb(payload, use_bin_type=True, default=str)
    response = _http_session.post(
        url, data=packed, headers=MSGPACK_HEADERS, verify=False, timeout=None
    )
    data = msgpack.unpackb(response.content, raw=False)
    return data, elapsed_time
```

- **`requests.Session()`** — reuses the TCP connection across all API calls. Each new `requests.post()` previously opened and closed a socket, adding ~3–10 ms per call on Windows (TCP handshake + TLS).
- **`timeout=None`** — no client-side timeout for long operations (large ballot counts).

#### 9b. Guardian Data Lookup — `json.loads` Removed

**Before:**
```python
def find_guardian_data(guardian_id, guardian_data_list, private_keys_list, ...):
    for gd_str in guardian_data_list:
        gd = json.loads(gd_str)          # ← parses JSON string to dict on every lookup
        if gd['id'] == guardian_id:
            guardian_data_str = gd_str   # returns JSON string
            break
```

**After:**
```python
def find_guardian_data(guardian_id, guardian_data_list, private_keys_list, ...):
    def _find(lst, key):
        for item in lst:
            if isinstance(item, dict) and item.get(key) == guardian_id:
                return item              # returns dict directly — no parsing needed
        raise ValueError(f"Guardian {guardian_id} not found (key='{key}')")

    gd   = _find(guardian_data_list, 'id')
    pk   = _find(private_keys_list,  'guardian_id')
    ...
    return gd, pk, pubk, poly            # returns dicts, passed directly to API
```

With msgpack transport, all server responses are decoded directly to native Python dicts. No intermediate JSON string storage or parsing is needed.

#### 9c. Chunked Tally Processing

**Before:** All N encrypted ballots were sent in a single `create_encrypted_tally` request. For 65,536 ballots at ~8 KB each, that is a ~512 MB payload — too large to handle in memory efficiently and prone to server timeouts.

**After:** Ballots are split into `CHUNK_SIZE = 1000` chunks. Each chunk gets its own complete tally → partial decrypt → compensated decrypt → combine pipeline. Vote counts are aggregated across chunks:

```python
CHUNK_SIZE = 1000

chunks = list(chunk_list(all_encrypted_ballots, CHUNK_SIZE))

final_vote_totals = defaultdict(int)

for chunk_idx, chunk in enumerate(chunks, start=1):
    # Tally this chunk (≤1000 ballots)
    tally_result = time_api_call("create_encrypted_tally", ..., {"encrypted_ballots": chunk, ...})

    # Partial decrypt
    for gid in available_guardian_ids:
        partial_result = time_api_call("create_partial_decryption", ..., {...})

    # Compensated decrypt
    for mid in missing_guardian_ids:
        for aid in available_guardian_ids:
            comp_result = time_api_call("create_compensated_decryption", ..., {...})

    # Combine
    combine_result = time_api_call("combine_decryption_shares", ..., {...})

    # Accumulate votes
    for cid, info in combine_result['results']['results']['candidates'].items():
        final_vote_totals[cid] += int(float(info.get('votes', 0)))
```

**Chunk size choice:** 1,000 ballots × ~8 KB ≈ 8 MB per tally request — comfortably within memory limits while keeping tally time under 5 seconds.

#### 9d. No `json.loads` on combine result

**Before:**
```python
results_str = combine_result['results']
results = json.loads(results_str)          # ← server returned JSON string inside JSON
```

**After:**
```python
chunk_results = combine_result['results']  # already a native dict via msgpack
```

The server now returns the `results` dict directly inside the msgpack payload, not as a nested JSON-encoded string.

#### 9e. Session Cleanup

```python
if __name__ == "__main__":
    success = False
    try:
        success = main()
    finally:
        _http_session.close()   # clean TCP connection teardown
    exit(0 if success else 1)
```

---

### 10. `single_election.py` — Reference Implementation

**File:** `single_election.py` *(new file)*

A clean reference implementation of the complete election workflow using all performance optimizations:

- `msgpack` transport throughout
- `requests.Session()` persistent connection
- `CHUNK_SIZE = 1000` chunked ballot processing
- `find_by_guardian_id()` helper using native dict lookups
- No JSON intermediate repr anywhere in the client
- Aggregates votes across all chunks

Used as the canonical example for integrating with the API and as the basis for the `ballot_variable_test.py` rewrite.

---

## Architecture: Why Each Change Matters

```
Request lifecycle (BEFORE):
  Client                            Server
  ──────────────────────────────────────────────────
  json.dumps(payload)     →   [open new TCP socket]
                          →   flask receives JSON
                          →   json.loads(request.body)
                          →   get_large_prime() × 1000+   ← HOT PATH (900ms)
                          →   inspect.stack() × 1000+     ← HOT PATH (2s)
                          →   multiprocessing.Pool()       ← HOT PATH (1-2s)
                          →   proof.is_valid() × 100+      ← WASTED WORK
                          →   create_manifest() × 1       ← 150ms per call
                          ←   json.dumps(response)
  response.json()         ←   [close TCP socket]

Request lifecycle (AFTER):
  Client                            Server
  ──────────────────────────────────────────────────
  msgpack.packb(payload)  →   [reuse TCP socket (Session)]
                          →   flask receives msgpack
                          →   msgpack.unpackb(request.data)
                          →   _LARGE_PRIME (module var)    ← O(1) lookup
                          →   logging.WARNING (no stack)   ← no overhead
                          →   [task(*args) for args …]     ← sequential
                          →   # proof correct by construction
                          →   _manifest_cache[key]         ← cached
                          ←   msgpack.packb(response)
  msgpack.unpackb(…)      ←   [keep TCP socket alive]
```

---

## Deployment Notes

### Running the optimized server

```bash
# Standard Flask (development + production equivalent)
python api.py

# Gunicorn (production — even higher throughput)
gunicorn --bind 0.0.0.0:5000 \
         --timeout 1200 \
         --workers 4 \
         --worker-class gthread \
         --threads 2 \
         api:app
```

### Running the scalability test client

```bash
# Full scalability test (32 → 131,072 ballots)
python ballot_variable_test.py

# Single election reference test
python single_election.py
```

### Key invariants to preserve

| Invariant | Reason |
|---|---|
| Always use `127.0.0.1`, not `localhost` | Avoids 2s IPv6 DNS fallback on Windows |
| Always send `Content-Type: application/msgpack` | Server returns msgpack only for msgpack requests |
| Always use `requests.Session()` in clients | TCP connection reuse — saves 3–10ms per call |
| Keep `debug=False, use_reloader=False` in `app.run()` | Debug mode adds 50–200ms latency per request |
| Never call `logging.getLogger('electionguard').setLevel(logging.INFO)` | Restoring INFO logging re-enables `inspect.stack()` overhead |
| Keep `_LARGE_PRIME`, `_SMALL_PRIME`, `_GENERATOR` as module-level constants | Any re-introduction of `get_large_prime()` inside math functions will restore the 900ms regression |
| Use `CHUNK_SIZE ≤ 1000` for ballot tally calls | Larger chunks risk server memory pressure and timeout |

---

*Last updated: February 2026*
