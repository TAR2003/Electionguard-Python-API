# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

**Electionguard-Python-API** is a comprehensive Python implementation of the ElectionGuard cryptographic protocol for secure, verifiable elections. It provides a Flask REST API with cryptographic operations including ballot encryption, guardian key ceremonies, tallying, and decryption with quorum support.

## Development Commands

### Setup and Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Run the main API server
python api.py

# Docker deployment
docker build -t electionguard-api .
docker run -p 5000:5000 electionguard-api
```

### Testing Commands
```bash
# Run comprehensive API tests
python test-api.py

# Run election simulation
python sample_election_simulation.py

# Test ballot sanitization
python test_ballot_sanitization.py

# Test individual components
python files_for_testing/main.py          # End-to-end election workflow
python files_for_testing/test.py          # API workflow tests
python files_for_testing/addquorum.py     # Quorum simulation
python files_for_testing/test_quorum.py   # Quorum-specific tests
```

### Code Quality
```bash
# Format code (as mentioned in README)
black .

# Run linting (pylint available in requirements.txt)
pylint electionguard/ services/ *.py

# Type checking (mypy available in requirements.txt)  
mypy electionguard/ services/ *.py
```

## Architecture Overview

### Core Architecture Pattern
This is a **layered architecture** with clear separation of concerns:

1. **API Layer** (`api.py`) - Flask REST endpoints with security features
2. **Service Layer** (`services/`) - Business logic for each operation
3. **Core Library** (`electionguard/`) - Cryptographic primitives and data structures
4. **Utilities** (`electionguard_tools/`) - Helpers, factories, testing strategies

### Key Architectural Concepts

**Guardian-Based Cryptography**: The system uses threshold cryptography where `k-of-n` guardians can decrypt results (e.g., 3 out of 5 guardians needed). Each guardian has:
- ElGamal key pairs for encryption/decryption
- Polynomial coefficients for secret sharing
- Backup capabilities for missing guardians

**Ballot Flow Architecture**:
1. **Manifest Creation** → Define election structure (parties, candidates, contests)
2. **Key Ceremony** → Guardians generate shared keys and commitments
3. **Ballot Encryption** → Plain text ballots encrypted with joint public key
4. **Ballot Box** → Encrypted ballots collected (CAST or AUDITED status)
5. **Tallying** → Homomorphic addition of encrypted votes
6. **Decryption** → Guardians provide shares to decrypt final tally

**Security & Privacy Features**:
- **Ballot Sanitization**: Nonces removed from CAST ballots (privacy), kept for AUDITED ballots (verification)
- **Post-Quantum Cryptography**: ML-KEM-1024 support via `pqcrypto` 
- **Zero-Knowledge Proofs**: Chaum-Pedersen and Schnorr proofs for verification
- **Compensated Decryption**: Missing guardians can be compensated by available ones

### Directory Structure Deep Dive

**`electionguard/`** - Core cryptographic library:
- `ballot.py`, `ballot_box.py` - Ballot data structures and state management
- `encrypt.py`, `elgamal.py` - Encryption primitives and ElGamal implementation
- `guardian.py`, `key_ceremony*.py` - Guardian management and key ceremonies
- `decryption*.py` - Decryption algorithms including compensated shares
- `tally.py` - Homomorphic tallying operations
- `proof.py`, `chaum_pedersen.py`, `schnorr.py` - Zero-knowledge proofs
- `group.py`, `constants.py` - Mathematical foundations (modular arithmetic)

**`services/`** - API business logic:
- `setup_guardians.py` - Guardian initialization and joint key generation
- `create_encrypted_ballot.py` - Ballot encryption service
- `create_encrypted_tally.py` - Tallying service
- `create_partial_decryption*.py` - Guardian decryption share services
- `create_compensated_decryption_shares.py` - Missing guardian compensation

**`files_for_testing/`** - Test scenarios:
- `main.py` - Complete election workflow simulation
- `test_quorum.py` - Quorum-based decryption testing
- `addquorum.py` - Quorum simulation with missing guardians

**Ballot Sanitization System** (security-critical):
- `ballot_sanitizer.py` - Core sanitization functions
- `ballot_publisher.py` - Secure ballot publication management
- Separates nonces based on ballot status (CAST vs AUDITED)

### Data Flow Patterns

**Request/Response Serialization**: The API handles complex cryptographic objects by serializing them as JSON strings. The pattern is:
```python
# API receives data as strings
guardian_data_str = request.json['guardian_data']  # String
# Convert to objects for processing
guardian_obj = from_raw(guardian_data_str)
# Return as strings
return {'result': to_raw(result_obj)}
```

**Guardian Data Management**: Each guardian has four key data structures that must be kept synchronized:
1. `guardian_data` - Guardian metadata and public information  
2. `private_key` - Guardian's private key for decryption
3. `public_key` - Guardian's public key for verification
4. `polynomial` - Guardian's polynomial for backup/compensation

**Quorum Operations**: The system supports `k-of-n` decryption where only `k` guardians out of `n` total are needed. Missing guardians are compensated using Lagrange interpolation.

## Important API Patterns

### Error Handling
All endpoints follow consistent error patterns with structured JSON responses and appropriate HTTP status codes.

### Security Headers
The API implements security headers, rate limiting, and payload size limits (1MB max).

### Environment Variables
- `MASTER_KEY_PQ` - Master key for post-quantum operations (required for production)
- `FLASK_ENV` - Environment setting (development/production)

## Testing Strategy

**Integration Tests**: `test-api.py` runs complete election workflows testing all API endpoints.

**Simulation Tests**: `sample_election_simulation.py` demonstrates the core cryptographic workflow without the API layer.

**Component Tests**: Files in `files_for_testing/` test specific scenarios like quorum operations and guardian compensation.

## Development Notes

**Cryptographic Dependencies**: The project requires `gmpy2` for fast arithmetic operations and `cryptography` for standard crypto primitives.

**JSON Schema Validation**: The `io/` directory contains request/response schemas for API endpoints.

**Docker Deployment**: Production deployment uses Gunicorn with 4 workers and 120-second timeout for cryptographic operations.

**Post-Quantum Ready**: Optional ML-KEM-1024 support for quantum-resistant encryption (requires `pqcrypto` package).

**Windows Development**: This codebase is actively developed on Windows with PowerShell support.