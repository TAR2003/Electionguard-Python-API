# ElectionGuard Python API - AI Coding Agent Instructions

## Architecture Overview

This is a **Flask REST API** implementing the Microsoft ElectionGuard cryptographic election protocol. The system enables secure, verifiable elections through a multi-guardian threshold cryptography scheme with homomorphic tallying.

### Core Data Flow
1. **Guardian Setup** → Creates guardians, generates joint public key via `KeyCeremonyMediator`
2. **Ballot Encryption** → Individual ballots encrypted with joint public key (homomorphic ElGamal)
3. **Tally Creation** → Homomorphically combines encrypted ballots without decryption
4. **Threshold Decryption** → Quorum of guardians decrypt tally (compensating for missing guardians)
5. **Result Computation** → Combines partial/compensated shares to reveal final vote counts

### Key Components

- **`api.py`** (1341 lines): Main Flask app with 15+ endpoints. Uses **threaded mode** and **500MB max payload** for large ballot files. Routes call service functions, never contain business logic.
- **`services/`**: Business logic layer. Each service is a pure function that takes parameters and returns dicts. Services handle ElectionGuard crypto operations.
- **`electionguard/`**: Core cryptographic library (Microsoft's ElectionGuard). Contains ballot encryption, key ceremonies, tallying, and threshold decryption primitives.
- **`electionguard_tools/`**: Factories, helpers, and orchestrators for building election manifests and test data.

## Critical Patterns

### Service Layer Pattern
**All API endpoints follow this pattern:**
```python
@app.route('/endpoint', methods=['POST'])
def endpoint_handler():
    data = request.get_json()
    # Minimal validation
    result = service_function(data['param1'], data['param2'])
    return jsonify(result)
```

Services are in `services/` and named `<action>_service()`. They:
- Accept primitive types and JSON strings (not ElectionGuard objects)
- Return dicts with JSON-serializable data
- Handle all ElectionGuard object creation/serialization internally
- Use `to_raw()` and `from_raw()` from `electionguard.serialize` for object serialization

### Guardian Data Structure
Guardians have 4 serialized components (all JSON strings):
1. **guardian_data**: Guardian object with ID, sequence, polynomial commitments
2. **private_key**: ElectionKeyPair (secret key + public key)
3. **public_key**: ElectionPublicKey for verification
4. **polynomial**: ElectionPolynomial for share computation

Helper function `find_guardian_data()` in tests shows how to extract these from lists by guardian_id.

### Ballot Workflow
- **PlaintextBallot**: Voter's selections before encryption
- **CiphertextBallot**: Encrypted ballot with proofs (stored, tallied)
- **SubmittedBallot**: Ballot with state (CAST/SPOILED) for tally
- Ballots use homomorphic ElGamal: tallying adds ciphertexts without decryption

### Threshold Decryption with Compensation
When missing guardians exist:
1. Available guardians compute **partial decryption shares**
2. Available guardians compute **compensated shares** for each missing guardian using backup polynomials
3. `combine_decryption_shares` merges all shares with Lagrange coefficients

## Configuration & Performance

### Large File Handling
The API is configured for **massive ballot files** (up to 2048+ ballots):
- `MAX_CONTENT_LENGTH = 500MB` in Flask config
- `timeout=300` (5 minutes) in client requests
- `threaded=True, debug=False, use_reloader=False` in `app.run()` - **critical for preventing timeouts**
- No request timeouts enforced server-side

### Testing Pattern
See `ballot_variable_test.py` for the canonical testing approach:
- Loop through `BALLOT_COUNTS = [64, 128, 256, 512, 1024, 2048]`
- Track timing with `timing_data` defaultdict
- Export results to text file with comparative analysis (current vs previous)
- Use `verify=False, timeout=300` in all `requests.post()` calls
- Clear `timing_data` between test runs

### Performance Testing
`ballot_variable_test.py` is the main performance harness:
- Tests complete election workflow at multiple scales
- Tracks API response times with `time_api_call()` wrapper
- Exports comparative timing data: ratios between ballot counts (e.g., 128 vs 64 = 2.000x)
- Appends results to `election_performance_results.txt` after each run

## Development Workflows

### Running the API
```bash
# Development (single-threaded, with debug - NOT for large files)
python api.py

# Production-like (threaded, no debug - REQUIRED for large operations)
# This is the default mode in api.py now
python api.py

# With Gunicorn (production deployment)
gunicorn --bind 0.0.0.0:5000 --timeout 1200 --workers 4 api:app
```

### Running Tests
```bash
# Full election simulation (64-2048 ballots, ~15-45 minutes)
python ballot_variable_test.py

# Single API test workflow
python test-api.py

# Benaloh challenge verification
python test_benaloh_final.py

# Ballot sanitization tests
python test_ballot_sanitization.py
```

### Key Files for Understanding
- `api.py` lines 412-1109: All endpoint definitions
- `services/setup_guardians.py`: Guardian creation pattern (representative of all services)
- `ballot_variable_test.py` lines 220-450: Complete election workflow example
- `files_for_testing/main.py`: End-to-end election with all steps

## ElectionGuard Specifics

### Manifest Creation
Elections require a `Manifest` with:
- `GeopoliticalUnit` (district)
- `Party` objects for each party
- `Candidate` objects for each candidate
- `Contest` with `SelectionDescription` for each candidate
- `BallotStyle` linking voters to contests

Use `create_election_manifest()` from `services.create_encrypted_ballot` as template.

### Serialization Rules
- **Never pass ElectionGuard objects directly** between functions
- Always use `to_raw(obj)` to serialize, `from_raw(json_string, Type)` to deserialize
- Guardian data is always transported as JSON strings, not Python objects
- CiphertextTally has custom serializers: `ciphertext_tally_to_raw()` and `raw_to_ciphertext_tally()`

### Common Gotchas
1. **Quorum validation**: Quorum must be ≤ number_of_guardians, typically `(n//2) + 1`
2. **Missing guardians**: Must provide compensated shares from **all available guardians** for **each missing guardian**
3. **Ballot IDs**: Must be unique strings, typically `f"ballot-{i+1}"`
4. **Joint public key**: Created during guardian setup, required for all encryption operations
5. **Commitment hash**: Election context hash, required for all ballot operations

## Security Features

The API implements:
- **Post-quantum cryptography**: ML-KEM-1024 (Kyber) encryption (optional, requires `pqcrypto`)
- **Ballot sanitization**: Removes nonces from published ballots (`ballot_sanitizer.py`)
- **Benaloh challenge**: Interactive ballot auditing (`services/benaloh_challenge.py`)
- **Rate limiting**: Simple in-memory rate limiter (use Redis in production)
- **HMAC verification**: Two-storage design for encrypted data + credentials

When modifying security code, preserve the two-storage pattern (encrypted payload + HMAC credentials).

## Adding New Endpoints

1. Create service function in `services/<feature>.py`
2. Add route in `api.py` following the pattern above
3. Create test in `test-api.py` or new test file
4. Add request/response JSON schemas in `io/` directory
5. Document in `APIformat.txt` (7559 lines of API docs)

## Common Tasks

**Add new ballot field**: Modify `PlaintextBallot` creation in `services/create_encrypted_ballot.py` → Update manifest with new contest/selection → Update tallying logic in `services/create_encrypted_tally.py`

**Change guardian count**: Update `NUMBER_OF_GUARDIANS` and `QUORUM` in test files → Ensure quorum validation passes → Adjust compensated decryption loops

**Optimize performance**: Check `timing_data` output → Profile service functions → Consider caching manifests/contexts → Verify threaded mode is enabled

**Debug crypto errors**: Enable logging with `logging.basicConfig(level=logging.DEBUG)` → Check ElectionGuard object serialization → Verify all guardians have matching election contexts
