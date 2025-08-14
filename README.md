# Quorum-Based Election Decryption

This implementation provides **true quorum-based decryption** for ElectionGuard elections, solving the problem where all guardians need to be present to decrypt election results.

## The Problem

The original API (`api.py`) required **ALL guardians** to be present to decrypt election results. This creates a single point of failure - if any guardian is unavailable, the entire election cannot be decrypted.

## The Solution

The new implementation (`api_quorum.py`) uses **ElectionGuard's compensated decryption** mechanism, which implements threshold cryptography using:

- **Polynomial Secret Sharing**: Secrets are split using Shamir's Secret Sharing scheme
- **Lagrange Coefficient Reconstruction**: Missing guardian shares are reconstructed mathematically
- **Compensated Decryption**: Available guardians can compute shares for missing guardians using their backup polynomial coordinates

## Key Features

### 1. True Quorum Support
- Only `quorum` number of guardians needed out of `total` guardians
- Example: 3 out of 5 guardians can decrypt the election
- Provides resilience against guardian unavailability

### 2. Cryptographic Security
- Uses ElectionGuard's proven cryptographic protocols
- Maintains end-to-end verifiability
- No compromise in security despite fewer guardians

### 3. Compensated Decryption
- Available guardians compute normal decryption shares
- Same guardians compute compensated shares for missing guardians
- Mathematical reconstruction using Lagrange coefficients

## API Endpoints

### Setup Election
```
POST /setup_guardians
{
    "number_of_guardians": 5,
    "quorum": 3,
    "party_names": ["Democratic", "Republican"],
    "candidate_names": ["Alice", "Bob"]
}
```

### Create Ballot
```
POST /create_encrypted_ballot
{
    "party_names": ["Democratic", "Republican"],
    "candidate_names": ["Alice", "Bob"],
    "candidate_name": "Alice",
    "ballot_id": "ballot-001",
    "joint_public_key": "...",
    "commitment_hash": "..."
}
```

### Create Tally
```
POST /create_encrypted_tally
{
    "party_names": ["Democratic", "Republican"],
    "candidate_names": ["Alice", "Bob"],
    "joint_public_key": "...",
    "commitment_hash": "...",
    "encrypted_ballots": [...]
}
```

### Decryption Process (3 steps)

#### 1. Create Partial Decryption (for available guardians)
```
POST /create_partial_decryption
{
    "guardian_id": "guardian-1",
    "guardian_data": [...],
    "party_names": ["Democratic", "Republican"],
    "candidate_names": ["Alice", "Bob"],
    "ciphertext_tally": "...",
    "submitted_ballots": [...],
    "joint_public_key": "...",
    "commitment_hash": "..."
}
```

#### 2. Create Compensated Decryption (for missing guardians)
```
POST /create_compensated_decryption
{
    "available_guardian_id": "guardian-1",
    "missing_guardian_id": "guardian-4",
    "guardian_data": [...],
    "party_names": ["Democratic", "Republican"],
    "candidate_names": ["Alice", "Bob"],
    "ciphertext_tally": "...",
    "submitted_ballots": [...],
    "joint_public_key": "...",
    "commitment_hash": "..."
}
```

#### 3. Combine Decryption Shares
```
POST /combine_decryption_shares
{
    "party_names": ["Democratic", "Republican"],
    "candidate_names": ["Alice", "Bob"],
    "joint_public_key": "...",
    "commitment_hash": "...",
    "ciphertext_tally": "...",
    "submitted_ballots": [...],
    "guardian_data": [...],
    "available_guardian_shares": {...},
    "compensated_shares": {...},
    "quorum": 3
}
```

## How It Works

### 1. Key Ceremony
- Guardians generate polynomial shares during setup
- Each guardian stores encrypted backup coordinates for other guardians
- Joint public key is created for encryption

### 2. Encryption Phase
- Ballots are encrypted using the joint public key
- Multiple ballots are tallied into a single ciphertext tally

### 3. Decryption Phase
- **Available guardians** compute their normal decryption shares
- **Same guardians** compute compensated shares for missing guardians using backup coordinates
- **DecryptionMediator** combines all shares using Lagrange coefficient reconstruction
- Final plaintext results are produced

## Mathematical Foundation

The system uses **Shamir's Secret Sharing** over elliptic curves:

1. **Secret Sharing**: The secret key is split into `n` shares such that any `k` shares can reconstruct the secret
2. **Lagrange Interpolation**: Missing shares are reconstructed using polynomial interpolation
3. **Compensated Decryption**: Available guardians use their backup polynomial coordinates to compute shares for missing guardians

## Files

- `api_quorum.py` - Main API with quorum support
- `test_quorum.py` - Comprehensive test suite
- `test_quorum_simple.py` - Simple comparison test
- `README_quorum.md` - This documentation

## Running the Tests

### Start the API server:
```bash
cd Microservice
python api_quorum.py
```

### Run comprehensive tests:
```bash
python test_quorum.py
```

### Run simple comparison test:
```bash
python test_quorum_simple.py
```

## Example Output

```
QUORUM vs ALL-GUARDIANS DECRYPTION COMPARISON
==============================================

Setting up: 5 guardians, 3 quorum
✅ Election setup complete
   - Total guardians: 5
   - Quorum needed: 3

✅ Ballot encrypted and tallied

🔹 SCENARIO 1: Quorum-based decryption (3 out of 5 guardians)
Available guardians: ['guardian-1', 'guardian-2', 'guardian-3']
Missing guardians: ['guardian-4', 'guardian-5']

✅ SUCCESS: Quorum-based decryption worked!
   - Used 3 out of 5 guardians
   - Results: Alice = 1 votes
   - Results: Bob = 0 votes
   - This is the NEW APPROACH - only quorum needed!

🔹 SCENARIO 2: What the old approach would require
❌ OLD APPROACH: Would need ALL 5 guardians to be present
❌ If any guardian is missing, election cannot be decrypted
❌ This is the problem we solved with quorum-based decryption!

SUMMARY:
✅ NEW: Only 3 out of 5 guardians needed (quorum)
❌ OLD: All 5 guardians required (single point of failure)
✅ NEW: Uses ElectionGuard's compensated decryption and Lagrange coefficients
✅ NEW: Provides cryptographic security with practical resilience
```

## Benefits

1. **Resilience**: Elections can be decrypted even if some guardians are unavailable
2. **Security**: No compromise in cryptographic security
3. **Verifiability**: Full end-to-end verifiability is maintained
4. **Practicality**: Reduces operational complexity and single points of failure
5. **Standard Compliance**: Uses standard ElectionGuard protocols

## Technical Details

The implementation leverages these ElectionGuard modules:
- `decryption_mediator.py` - Orchestrates the decryption process
- `decryption_share.py` - Handles individual guardian shares
- `election_polynomial.py` - Manages polynomial operations
- `decrypt_with_shares.py` - Combines shares for final decryption

This provides a production-ready, cryptographically secure quorum-based election system.
