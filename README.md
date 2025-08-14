

# Electionguard-Python-API

## Overview

**Electionguard-Python-API** is a comprehensive, modular, and extensible Python implementation of the ElectionGuard cryptographic protocol. It provides secure, verifiable, and privacy-preserving election workflows, including ballot encryption, guardian key ceremonies, tallying, and decryption. The project is designed for research, simulation, and real-world deployment, with a modern API and robust testing.

---

## Table of Contents
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Core Modules & Files](#core-modules--files)
- [API Endpoints](#api-endpoints)
- [Testing & Simulation](#testing--simulation)
- [Contributing](#contributing)
- [License](#license)

---

## Project Structure

```
Electionguard-Python-API/
├── api.py                  # Main Flask API server
├── Dockerfile              # Containerization for deployment
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
├── sample_election_simulation.py # Election simulation script
├── test-api.py             # API integration tests
├── APIformat.txt           # API data format reference
├── a.txt                   # Output/debug file
├── compensated_request.json
├── create_encrypted_ballot_response.json
├── guardian_data.json
├── __init__.py             # Package marker
├── electionguard/          # Core cryptographic library
│   ├── ballot.py           # Ballot data structures & logic
│   ├── ballot_box.py       # Ballot box state & casting
│   ├── ...                 # (Many cryptographic modules)
│   └── __init__.py         # Library imports
├── electionguard_tools/    # Utilities, factories, helpers
│   ├── factories/          # Ballot & election data factories
│   ├── helpers/            # Election builder, export, orchestrators
│   ├── scripts/            # Sample data generators
│   ├── strategies/         # Property-based testing strategies
│   └── __init__.py         # Tools imports
├── files_for_testing/      # Test scripts & sample data
│   ├── main.py             # End-to-end election workflow
│   ├── test.py             # API workflow test
│   ├── addquorum.py        # Quorum simulation
│   └── ...                 # (Other test files)
├── io/                     # JSON I/O schemas
│   ├── ...                 # (Request/response formats)
├── services/               # API service logic
│   ├── ...                 # (Service endpoints)
└── ...
```

---

## Setup & Installation

1. **Clone the repository:**
  ```sh
  git clone https://github.com/TAR2003/Electionguard-Python-API.git
  cd Electionguard-Python-API
  ```
2. **Install dependencies:**
  ```sh
  pip install -r requirements.txt
  ```
3. **Run the API server:**
  ```sh
  python api.py
  # Or with Docker
  docker build -t electionguard-api .
  docker run -p 5000:5000 electionguard-api
  ```

---

## Core Modules & Files

### Top-Level Files
- **api.py**: Main Flask API server. Implements endpoints for election setup, ballot encryption, tallying, and decryption. Integrates all core modules and services.
- **Dockerfile**: Production-ready containerization. Uses Gunicorn for scalable deployment.
- **requirements.txt**: All Python dependencies, including Flask, cryptography, and testing tools.
- **sample_election_simulation.py**: Simulates a full election workflow for research and demonstration.
- **test-api.py**: Automated API integration tests using requests.
- **APIformat.txt**: Reference for all API request/response data formats.
- **a.txt**: Output/debug file for test results and logs.
- **compensated_request.json, create_encrypted_ballot_response.json, guardian_data.json**: Sample data and schema files for API requests/responses.
- **__init__.py**: Marks the root as a Python package.

### `electionguard/` - Core Cryptography
- **ballot.py**: Ballot data structures, encryption, and validation logic.
- **ballot_box.py**: Ballot box state management, casting, and spoiling ballots.
- **constants.py**: Mathematical constants (primes, generators) for cryptographic operations.
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
