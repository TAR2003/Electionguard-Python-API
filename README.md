
# ElectionGuard Python API

This repository contains a Python-based implementation of the ElectionGuard API, providing a secure and verifiable voting system. It includes a Flask-based API for interacting with the ElectionGuard protocol, as well as a sample simulation to demonstrate its end-to-end functionality. The API also features post-quantum cryptographic enhancements for long-term security.

## Table of Contents

- [About The Project](#about-the-project)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage](#usage)
  - [Running the API Server](#running-the-api-server)
  - [Running the Sample Election Simulation](#running-the-sample-election-simulation)
- [API Reference](#api-reference)
  - [Health Check](#health-check)
  - [Election Setup](#election-setup)
  - [Ballot Encryption](#ballot-encryption)
  - [Tallying and Decryption](#tallying-and-decryption)
- [File Structure](#file-structure)
- [Docker](#docker)
  - [Building the Docker Image](#building-the-docker-image)
  - [Running the Docker Container](#running-the-docker-container)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## About The Project

This project provides a Python implementation of Microsoft's ElectionGuard, a free and open-source software development kit (SDK) that enables end-to-end verifiability and security for elections. It aims to make voting more secure, transparent, and publicly verifiable.

This implementation includes:

- A Flask-based API to expose ElectionGuard's core functionalities.
- An end-to-end election simulation demonstrating the entire voting process.
- Integration of post-quantum cryptography (Kyber1024) to ensure long-term security against future threats.
- A clear and modular code structure for easy understanding and extension.

## Getting Started

To get a local copy up and running, follow these simple steps.

### Prerequisites

This project uses Python 3.10+. You will also need to install the dependencies listed in the `requirements.txt` file.

### Installation

1. **Clone the repository:**

   ```sh
   git clone https://github.com/your_username/Electionguard-Python-API.git
   cd Electionguard-Python-API
   ```

2. **Create and activate a virtual environment (recommended):**

   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. **Install the dependencies:**

   ```sh
   pip install -r requirements.txt
   ```

## Usage

This project can be used in two main ways: by running the API server or by running the sample election simulation.

### Running the API Server

The API server provides a way to interact with the ElectionGuard protocol through a series of RESTful endpoints.

To start the API server, run the following command:

```sh
python api.py
```

The server will start on `http://127.0.0.1:5000`.

### Running the Sample Election Simulation

The sample election simulation demonstrates the entire end-to-end process of an election, from setting up guardians to tallying and decrypting the votes.

To run the simulation, execute the following command:

```sh
python sample_election_simulation.py
```

The script will print the election results to the console.

## API Reference

The following are the main endpoints provided by the API:

### Health Check

- **GET /health**: Checks the health of the API.

### Election Setup

- **POST /setup_guardians**: Sets up the election guardians and generates a joint public key.
- **POST /create_election_manifest**: Creates the election manifest.

### Ballot Encryption

- **POST /create_encrypted_ballot**: Encrypts a single ballot.

### Tallying and Decryption

- **POST /create_encrypted_tally**: Tallies all the encrypted ballots.
- **POST /create_partial_decryption**: Computes a guardian's partial decryption of the tally.
- **POST /combine_decryption_shares**: Combines the partial decryptions to get the final election results.

For more details on the API request and response formats, please refer to the `APIformat.txt` file.

## File Structure

Here is a brief overview of the project's file structure:

```
├── electionguard/              # Core ElectionGuard library
├── electionguard_tools/        # Tools for working with ElectionGuard
├── services/                   # Business logic for the API endpoints
├── files_for_testing/          # Files for testing purposes
├── io/                         # Input/output files for the API
├── __init__.py                 # Package initializer
├── api.py                      # Flask API application
├── sample_election_simulation.py # End-to-end election simulation
├── Dockerfile                  # Docker configuration
├── requirements.txt            # Project dependencies
└── README.md                   # This file
```

## Docker

This project includes a `Dockerfile` to allow you to build and run the application in a containerized environment.

### Building the Docker Image

To build the Docker image, run the following command from the root of the project:

```sh
docker build -t electionguard-api .
```

### Running the Docker Container

To run the Docker container, use the following command:

```sh
docker run -p 5000:5000 electionguard-api
```

The API will be accessible at `http://localhost:5000`.

## Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License. See the `LICENSE` file for more information.

## Contact

Your Name - your_email@example.com

Project Link: [https://github.com/your_username/Electionguard-Python-API](https://github.com/your_username/Electionguard-Python-API)
