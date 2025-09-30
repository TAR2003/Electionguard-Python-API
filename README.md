
# ElectionGuard Python API

## Overview

**ElectionGuard Python API** is a comprehensive, production-ready implementation of the Microsoft ElectionGuard cryptographic election protocol. This system provides secure, verifiable, and privacy-preserving election workflows including guardian key ceremonies, ballot encryption, homomorphic tallying, threshold decryption, and ballot auditing capabilities. The project features a complete Flask REST API with advanced security measures, ballot sanitization, and Benaloh challenge verification.

---

## Table of Contents
- [Features](#features)
- [Project Architecture](#project-architecture)
- [Installation & Setup](#installation--setup)
- [Core Components](#core-components)
- [API Endpoints](#api-endpoints)
- [Security Features](#security-features)
- [Testing & Simulation](#testing--simulation)
- [Configuration](#configuration)
- [Development](#development)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

---

## Features

### Core ElectionGuard Protocol
- **Guardian Key Ceremonies**: Multi-party key generation with quorum-based threshold cryptography
- **Ballot Encryption**: Individual ballot encryption with homomorphic properties
- **Homomorphic Tallying**: Privacy-preserving vote aggregation
- **Threshold Decryption**: Quorum-based decryption with compensated shares for missing guardians
- **Zero-Knowledge Proofs**: Chaum-Pedersen and Schnorr proofs for verifiability

### Advanced Security Features
- **Ballot Sanitization**: Secure nonce extraction for cast vs. audited ballot publication
- **Benaloh Challenge**: Interactive ballot verification system
- **Post-Quantum Cryptography**: ML-KEM-1024 (Kyber) support for future-proofing
- **Rate Limiting**: Protection against API abuse
- **Security Headers**: Comprehensive HTTP security headers
- **Input Validation**: Robust parameter validation and sanitization

### Production-Ready API
- **RESTful Endpoints**: Complete HTTP API with JSON schemas
- **Containerization**: Docker support with Gunicorn for scalable deployment
- **Health Monitoring**: System status and diagnostic endpoints
- **Error Handling**: Structured error responses with appropriate HTTP status codes
- **Logging**: Comprehensive audit trails and debugging support

---

## Project Architecture

```
ElectionGuard-Python-API/
├── 📄 Core API & Configuration
│   ├── api.py                              # Main Flask REST API server
│   ├── Dockerfile                          # Production containerization
│   ├── requirements.txt                    # Python dependencies
│   ├── APIformat.txt                       # Complete API documentation (7559 lines)
│   ├── WARP.md                            # Development guide for WARP.dev
│   └── __init__.py                        # Package initialization
│
├── 🔐 Security & Verification
│   ├── ballot_sanitizer.py               # Nonce extraction and ballot sanitization
│   ├── ballot_publisher.py               # Secure ballot publication management
│   ├── test_ballot_sanitization.py       # Sanitization testing
│   ├── BALLOT_SANITIZATION_README.md     # Sanitization documentation
│   ├── test_benaloh_challenge.py         # Benaloh challenge tests
│   ├── test_benaloh_simple.py           # Simplified challenge tests
│   ├── test_benaloh_final.py             # Comprehensive challenge tests
│   ├── BENALOH_CHALLENGE_IMPLEMENTATION.md # Challenge documentation
│   ├── secure_api_example.py             # Secure API integration example
│   ├── test_secure_api.py                # Security testing
│   └── verify_api_integration.py         # Integration verification
│
├── 🏗️ ElectionGuard Core Library
│   └── electionguard/                     # Core cryptographic implementation
│       ├── ballot.py                     # Ballot data structures and encryption
│       ├── ballot_box.py                 # Ballot box state management
│       ├── ballot_code.py                # Ballot tracking codes
│       ├── ballot_compact.py             # Compact ballot representations
│       ├── ballot_validator.py           # Ballot validation logic
│       ├── big_integer.py                # Large integer operations
│       ├── byte_padding.py               # Cryptographic padding utilities
│       ├── chaum_pedersen.py             # Chaum-Pedersen zero-knowledge proofs
│       ├── constants.py                  # Mathematical constants and parameters
│       ├── data_store.py                 # Data persistence layer
│       ├── decrypt_with_secrets.py       # Secret-based decryption
│       ├── decrypt_with_shares.py        # Share-based threshold decryption
│       ├── decryption.py                 # Core decryption algorithms
│       ├── decryption_mediator.py        # Decryption orchestration
│       ├── decryption_share.py           # Decryption share management
│       ├── discrete_log.py               # Discrete logarithm computations
│       ├── election.py                   # Election context and configuration
│       ├── election_object_base.py       # Base classes for election objects
│       ├── election_polynomial.py        # Polynomial operations for key ceremony
│       ├── elgamal.py                    # ElGamal encryption implementation
│       ├── encrypt.py                    # Ballot encryption services
│       ├── group.py                      # Modular arithmetic and group theory
│       ├── guardian.py                   # Guardian management and operations
│       ├── hash.py                       # Cryptographic hashing functions
│       ├── hmac.py                       # HMAC authentication
│       ├── key_ceremony.py               # Key generation ceremonies
│       ├── key_ceremony_mediator.py      # Key ceremony orchestration
│       ├── logs.py                       # Logging infrastructure
│       ├── manifest.py                   # Election manifest definitions
│       ├── nonces.py                     # Cryptographic nonce management
│       ├── proof.py                      # Zero-knowledge proof systems
│       ├── py.typed                      # Type hint marker
│       ├── scheduler.py                  # Task scheduling utilities
│       ├── schnorr.py                    # Schnorr signature proofs
│       ├── serialize.py                  # Object serialization/deserialization
│       ├── singleton.py                  # Singleton pattern implementation
│       ├── tally.py                      # Homomorphic tallying operations
│       ├── type.py                       # Type definitions and aliases
│       ├── utils.py                      # General utility functions
│       └── __init__.py                   # Library exports (746 lines)
│
├── 🛠️ Development Tools & Utilities
│   └── electionguard_tools/              # Development and testing utilities
│       ├── factories/                    # Data generation factories
│       │   ├── ballot_factory.py        # Ballot generation utilities
│       │   ├── election_factory.py      # Election setup factories
│       │   └── __init__.py              # Factory exports
│       ├── helpers/                      # Development helpers
│       │   ├── election_builder.py      # Election configuration builder
│       │   ├── export.py                # Data export utilities
│       │   ├── key_ceremony_orchestrator.py # Key ceremony automation
│       │   ├── tally_accumulate.py      # Tally accumulation helpers
│       │   ├── tally_ceremony_orchestrator.py # Tally ceremony automation
│       │   └── __init__.py              # Helper exports
│       ├── scripts/                      # Sample data generation
│       │   ├── sample_generator.py      # Election sample data generator
│       │   └── __init__.py              # Script exports
│       ├── strategies/                   # Property-based testing strategies
│       │   ├── election.py              # Election object generation strategies
│       │   ├── elgamal.py               # ElGamal key generation strategies
│       │   ├── group.py                 # Group element generation strategies
│       │   └── __init__.py              # Strategy exports
│       └── __init__.py                  # Tools package exports (181 lines)
│
├── 🔌 API Services Layer
│   └── services/                         # Business logic services
│       ├── benaloh_challenge.py         # Benaloh challenge verification
│       ├── combine_decryption_shares.py # Share combination service
│       ├── create_compensated_decryption_shares.py # Missing guardian compensation
│       ├── create_encrypted_ballot.py   # Ballot encryption service
│       ├── create_encrypted_tally.py    # Tally creation service
│       ├── create_partial_decryption.py # Partial decryption service
│       ├── create_partial_decryption_shares.py # Decryption share creation
│       ├── decrypt.py                   # Decryption service
│       ├── encrypt.py                   # Encryption service
│       ├── guardian_key_ceremony.py     # Guardian ceremony service
│       ├── setup_guardians.py          # Guardian setup service
│       └── __init__.py                  # Service exports
│
├── 🧪 Testing & Simulation
│   ├── sample_election_simulation.py    # Complete election simulation (786 lines)
│   ├── test-api.py                      # Comprehensive API integration tests
│   └── files_for_testing/               # Test scenarios and data
│       ├── main.py                      # End-to-end election workflow (700 lines)
│       ├── test.py                      # API workflow testing (274 lines)
│       ├── addquorum.py                 # Quorum simulation testing
│       ├── test_quorum.py               # Quorum-specific test cases
│       ├── test_final.py                # Final integration tests
│       ├── altered_main.py              # Modified workflow tests
│       ├── another.py                   # Additional test scenarios
│       ├── function_for_api.py          # API helper functions
│       ├── hashtest.py                  # Hash function testing
│       ├── interactive.py               # Interactive testing utilities
│       ├── partial_decryption.py        # Partial decryption testing
│       ├── a.json, ab.json              # Test data files
│       ├── compensated_request.json     # Compensation test data
│       ├── election_results.json        # Sample election results
│       ├── guardian_data.json           # Guardian test data
│       └── a.txt                        # Test output logs
│
├── 📊 API Schemas & I/O
│   └── io/                              # Request/response schemas
│       ├── benaloh_challenge_request.json
│       ├── benaloh_challenge_response.json
│       ├── combine_decryption_shares_request.json
│       ├── combine_decryption_shares_response.json
│       ├── create_compensated_decryption_request.json
│       ├── create_compensated_decryption_response.json
│       ├── create_encrypted_ballot_request.json
│       ├── create_encrypted_ballot_response.json
│       ├── create_encrypted_tally_request.json
│       ├── create_encrypted_tally_response.json
│       ├── create_partial_decryption_response.json
│       ├── partial_decryption_request.json
│       ├── setup_guardians_data.json
│       └── setup_guardians_response.json
│
└── 📁 Generated Outputs & Logs
    ├── a.txt                            # General output logs
    ├── compensated_request.json         # Generated compensation requests
    ├── create_encrypted_ballot_response.json # Sample ballot responses
    ├── guardian_data.json               # Generated guardian data
    ├── sanitized_audited_ballot.json    # Sanitized audited ballots
    └── sanitized_cast_ballot.json       # Sanitized cast ballots
```

---

## Installation & Setup

### Prerequisites
- **Python 3.10+**: Required for modern type hints and language features
- **Git**: For repository cloning and version control
- **Docker** (optional): For containerized deployment

### Dependencies
The project includes comprehensive dependencies for cryptography, web framework, testing, and development:

**Core Runtime:**
- `flask` - Web framework for REST API
- `cryptography` - Cryptographic primitives
- `gmpy2` - High-performance arithmetic
- `python-dotenv` - Environment variable management
- `pqcrypto` - Post-quantum cryptography (optional)

**Development & Testing:**
- `pytest`, `pytest-mock` - Testing framework
- `hypothesis` - Property-based testing
- `black` - Code formatting
- `pylint`, `mypy` - Code quality and type checking
- `coverage` - Test coverage analysis

**Production:**
- `gunicorn` - WSGI HTTP server
- `psycopg2-binary` - PostgreSQL adapter
- `pymongo` - MongoDB driver

### Installation Steps

1. **Clone the Repository**
   ```bash
   git clone https://github.com/TAR2003/Electionguard-Python-API.git
   cd Electionguard-Python-API
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration** (Optional)
   ```bash
   # Create .env file for production settings
   echo "MASTER_KEY_PQ=your-post-quantum-master-key" > .env
   echo "FLASK_ENV=development" >> .env
   ```

4. **Run the API Server**
   ```bash
   # Development mode
   python api.py
   
   # Production mode with Gunicorn
   gunicorn --bind 0.0.0.0:5000 --timeout 120 --workers 4 api:app
   ```

5. **Docker Deployment** (Alternative)
   ```bash
   # Build container
   docker build -t electionguard-api .
   
   # Run container
   docker run -p 5000:5000 electionguard-api
   ```

6. **Verify Installation**
   ```bash
   # Test API health
   curl http://localhost:5000/api/health
   
   # Run integration tests
   python test-api.py
   ```

---

## API Endpoints

The Flask REST API provides comprehensive endpoints for all ElectionGuard operations:

### Guardian & Key Management
- `POST /setup_guardians` - Initialize guardians and generate joint public key
- `POST /init_guardian_ceremony` - Start guardian key ceremony
- `POST /submit_guardian_keys` - Submit guardian public keys
- `POST /finalize_guardian_ceremony` - Complete key ceremony
- `GET /ceremony_status` - Check key ceremony status

### Ballot Operations
- `POST /create_encrypted_ballot` - Encrypt individual voter ballots
- `POST /create_encrypted_tally` - Generate homomorphic tally from ballots

### Decryption & Results
- `POST /create_partial_decryption` - Generate guardian decryption shares
- `POST /create_compensated_decryption` - Handle missing guardian compensation
- `POST /combine_decryption_shares` - Combine shares for final results

### Verification & Security
- `POST /benaloh_challenge` - Perform Benaloh challenge verification
- `GET /api/health` - System health and status check

### Request/Response Format
All endpoints use JSON with comprehensive schema validation. See `APIformat.txt` (7,559 lines) for complete specifications.

**Example Request:**
```json
{
  "party_names": ["Democratic Party", "Republican Party"],
  "candidate_names": ["Alice Johnson", "Bob Smith"],
  "candidate_name": "Alice Johnson",
  "ballot_id": "ballot-001",
  "joint_public_key": "...",
  "commitment_hash": "..."
}
```

**Example Response:**
```json
{
  "status": "success",
  "encrypted_ballot": "...",
  "encrypted_ballot_with_nonce": "...",
  "ballot_hash": "...",
  "tracking_code": "..."
}
```

---

## Security Features

### Ballot Sanitization System
**Purpose**: Secure publication of ballots based on status (CAST vs AUDITED)

**Cast Ballots:**
- Nonces removed for privacy protection
- Encrypted values published for verification
- Zero-knowledge proofs preserved

**Audited Ballots:**
- All nonces revealed for full verification
- Complete decryption possible
- Audit trail maintained

**Implementation:**
```python
from ballot_sanitizer import prepare_ballot_for_publication

# For cast ballots - nonces hidden
cast_result = prepare_ballot_for_publication(ballot_json, "CAST")

# For audited ballots - nonces revealed
audited_result = prepare_ballot_for_publication(ballot_json, "AUDITED")
```

### Benaloh Challenge Verification
**Purpose**: Interactive ballot verification system for voter confidence

**Process:**
1. Voter chooses to challenge or cast ballot
2. If challenged, nonces are revealed
3. System decrypts ballot and verifies choices
4. Voter confirms correct encryption

**Features:**
- Cryptographically correct ElGamal decryption
- Individual selection verification
- Candidate choice validation
- Complete audit trail

### Post-Quantum Cryptography
**Algorithm**: ML-KEM-1024 (NIST-approved Kyber variant)
**Purpose**: Future-proofing against quantum computing threats

**Implementation:**
- Optional PQC layer for sensitive data
- Hybrid classical/post-quantum approach
- Configurable via environment variables

### Security Headers & Protection
- **Rate Limiting**: Request throttling to prevent abuse
- **Input Validation**: Comprehensive parameter sanitization
- **HTTPS Enforcement**: Strict transport security
- **Content Security**: XSS and injection protection
- **Payload Limits**: 1MB maximum request size

---

## Configuration

### Environment Variables
```bash
# Post-quantum cryptography
MASTER_KEY_PQ=your-256-bit-master-key

# Flask configuration
FLASK_ENV=production
FLASK_APP=api.py

# Gunicorn settings
GUNICORN_TIMEOUT=120
GUNICORN_WORKERS=4
```

### Application Settings
- **Scrypt Parameters**: N=65536, r=8, p=1 (optimized for security/performance)
- **AES Encryption**: 256-bit keys with authenticated encryption
- **Password Generation**: 256-bit entropy for maximum security
- **Session Management**: Secure token-based authentication

---

## Core Components

### ElectionGuard Core Library (`electionguard/`)

The core library implements the complete ElectionGuard cryptographic protocol with 40+ modules:

**Ballot Management:**
- `ballot.py` - Core ballot data structures and encryption logic
- `ballot_box.py` - Ballot box state management and casting operations
- `ballot_code.py` - Ballot tracking and identification codes
- `ballot_compact.py` - Compact ballot representations for efficiency
- `ballot_validator.py` - Ballot validation and integrity checking

**Cryptographic Primitives:**
- `elgamal.py` - ElGamal encryption implementation
- `encrypt.py` - Ballot encryption services and device management
- `group.py` - Modular arithmetic and mathematical group operations
- `constants.py` - Mathematical constants and cryptographic parameters
- `big_integer.py` - Large integer arithmetic operations
- `hash.py` - Cryptographic hashing functions
- `hmac.py` - Hash-based message authentication codes

**Guardian & Key Management:**
- `guardian.py` - Guardian lifecycle and key management
- `key_ceremony.py` - Key generation ceremonies and protocols
- `key_ceremony_mediator.py` - Key ceremony orchestration
- `election_polynomial.py` - Polynomial operations for threshold cryptography

**Decryption & Tallying:**
- `decrypt_with_secrets.py` - Secret-based decryption for testing
- `decrypt_with_shares.py` - Production threshold decryption
- `decryption.py` - Core decryption algorithms
- `decryption_mediator.py` - Decryption process orchestration
- `decryption_share.py` - Individual guardian decryption shares
- `tally.py` - Homomorphic tallying operations

**Zero-Knowledge Proofs:**
- `proof.py` - General proof system infrastructure
- `chaum_pedersen.py` - Chaum-Pedersen zero-knowledge proofs
- `schnorr.py` - Schnorr signature proofs

**Election Configuration:**
- `manifest.py` - Election manifest and contest definitions
- `election.py` - Election context and configuration
- `election_object_base.py` - Base classes for election objects

**Utilities & Infrastructure:**
- `serialize.py` - Object serialization and deserialization
- `data_store.py` - Data persistence abstraction layer
- `logs.py` - Comprehensive logging infrastructure
- `utils.py` - General utility functions
- `type.py` - Type definitions and aliases
- `nonces.py` - Cryptographic nonce management
- `discrete_log.py` - Discrete logarithm computations
- `byte_padding.py` - Cryptographic padding utilities
- `scheduler.py` - Task scheduling and coordination
- `singleton.py` - Singleton pattern implementation
- **encrypt.py**: Ballot encryption algorithms and device logic.
- **guardian.py**: Guardian key management, backup, and verification.
- **decryption.py, decryption_mediator.py, decryption_share.py**: Tally and ballot decryption logic, including compensated shares.
- **elgamal.py**: ElGamal encryption primitives.
- **group.py**: Group theory and modular arithmetic utilities.
- **manifest.py**: Election manifest and contest/candidate definitions.
- **key_ceremony.py, key_ceremony_mediator.py**: Guardian key ceremony orchestration.
- **logs.py**: Logging utilities.
- **serialize.py**: Serialization/deserialization of cryptographic objects.
- **schnorr.py, proof.py, chaum_pedersen.py**: Zero-knowledge proof implementations.
- **utils.py, type.py, singleton.py, scheduler.py, byte_padding.py, big_integer.py, nonces.py, discrete_log.py, election_object_base.py, election_polynomial.py, tally.py, ballot_code.py, ballot_compact.py, ballot_validator.py, hash.py, hmac.py**: Supporting cryptographic and utility modules.
- **__init__.py**: Aggregates all core modules for easy import.

### `electionguard_tools/` - Utilities & Testing
- **factories/**: Factories for generating ballots, elections, and test data.
- **helpers/**: ElectionBuilder, export utilities, orchestrators for key ceremonies and tallying.
- **scripts/**: Sample data generators for testing and simulation.
- **strategies/**: Property-based testing strategies for cryptographic objects.
- **__init__.py**: Imports and exposes all utilities for testing and development.

### `files_for_testing/` - Test Scripts & Data
- **main.py**: End-to-end election workflow simulation.
- **test.py**: API workflow test script.
- **addquorum.py**: Quorum simulation and testing.
- **Other files**: Additional test scripts, sample data, and helper functions for robust testing.

### `io/` - JSON Schemas
- **combine_decryption_shares_request.json, ...**: Defines request/response formats for API endpoints, ensuring strict schema validation.

### `services/` - API Service Logic
- **combine_decryption_shares.py, create_compensated_decryption_shares.py, ...**: Implements business logic for each API endpoint, including ballot encryption, tallying, and decryption.
- **__init__.py**: Marks the directory as a Python package.

---

## API Endpoints

The API exposes endpoints for:
- Guardian setup and key ceremonies
- Ballot encryption and submission
- Tallying and decryption (including compensated shares)
- Data retrieval and simulation

See `APIformat.txt` for detailed request/response formats and example payloads.

---

## Testing & Simulation

- **Unit & Integration Tests:**
  - Run `test-api.py` and scripts in `files_for_testing/` for automated and manual testing.
- **Simulation:**
  - Use `sample_election_simulation.py` and `main.py` for full election workflow simulations.

---

## Contributing

1. Fork the repository and create a feature branch.
2. Write clear, well-documented code and tests.
3. Submit a pull request with a detailed description.
4. Follow PEP8 and use `black` for formatting.

---

## License

This project is licensed under the MIT License. See `LICENSE` for details.

---

## Acknowledgements

- [ElectionGuard](https://www.microsoft.com/en-us/security/business/electionguard) cryptographic protocol
- All contributors and open-source libraries

---

## Visual Structure

> The codebase is modular, extensible, and designed for clarity. Each folder and file is purpose-built for cryptographic security, verifiability, and ease of testing. The API is production-ready and containerized for scalable deployment.

---

**For questions, issues, or contributions, please open an issue or contact the maintainer.**
