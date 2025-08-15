#!/usr/bin/env python
"""
Test script for the new setup_guardian API endpoint.
This demonstrates how a guardian would generate their own keys and send only the public key.
"""

import requests
import json
from electionguard.elgamal import ElGamalKeyPair, ElGamalSecretKey, ElGamalPublicKey
from electionguard.group import ElementModQ, ElementModP, g_pow_p, int_to_q, rand_q
from electionguard.election_polynomial import generate_polynomial
from electionguard.serialize import to_raw


def generate_guardian_keys():
    """
    Simulate a guardian generating their own private key, public key, and polynomial.
    In practice, this would happen on the guardian's local machine.
    """
    # Generate private key
    private_key = rand_q()

    # Generate public key from private key
    public_key = g_pow_p(private_key)

    # Generate polynomial (guardian keeps this secret)
    polynomial = generate_polynomial(3)  # assuming quorum of 3

    return {
        'private_key': private_key,
        'public_key': public_key,
        'polynomial': polynomial
    }


def test_setup_guardian_endpoint():
    """
    Test the new setup_guardian endpoint.
    """
    # Simulate guardian generating keys locally
    guardian_keys = generate_guardian_keys()

    # Guardian only sends the public key to the server
    guardian_data = {
        'guardian_id': 'guardian_1',
        'sequence_order': 1,
        # Only public key sent
        'public_key': str(int(guardian_keys['public_key'])),
        'number_of_guardians': 3,
        'quorum': 3,
        'party_names': ['Democratic Party', 'Republican Party'],
        'candidate_names': ['Alice Johnson', 'Bob Smith']
    }

    # Send request to API
    url = 'http://localhost:5000/setup_guardian'

    try:
        response = requests.post(url, json=guardian_data)

        if response.status_code == 200:
            result = response.json()
            print("✅ Setup guardian successful!")
            print(f"Guardian ID: {result['guardian_id']}")
            print(f"Sequence Order: {result['sequence_order']}")
            print(f"Status: {result['status']}")

            # The guardian keeps their private key and polynomial locally
            print(f"\n🔒 Guardian keeps locally:")
            print(f"Private Key: {int(guardian_keys['private_key'])}")
            print(f"Polynomial: [hidden]")

            print(f"\n🌐 Server response (public information only):")
            print(f"Election Public Key: [serialized]")
            print(f"Guardian Data: [serialized]")

            return True

        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Message: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Make sure the API server is running on http://localhost:5000")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_multiple_guardians():
    """
    Test setting up multiple guardians independently.
    """
    print("\n" + "="*50)
    print("Testing Multiple Guardian Setup")
    print("="*50)

    guardians_info = []

    for i in range(1, 4):  # 3 guardians
        print(f"\n--- Setting up Guardian {i} ---")

        # Each guardian generates their own keys
        guardian_keys = generate_guardian_keys()

        guardian_data = {
            'guardian_id': f'guardian_{i}',
            'sequence_order': i,
            'public_key': str(int(guardian_keys['public_key'])),
            'number_of_guardians': 3,
            'quorum': 3,
            'party_names': ['Democratic Party', 'Republican Party'],
            'candidate_names': ['Alice Johnson', 'Bob Smith']
        }

        # Store guardian info (in practice, each guardian keeps their own secrets)
        guardians_info.append({
            'guardian_id': f'guardian_{i}',
            'private_key': guardian_keys['private_key'],
            'public_key': guardian_keys['public_key'],
            'polynomial': guardian_keys['polynomial']
        })

        url = 'http://localhost:5000/setup_guardian'

        try:
            response = requests.post(url, json=guardian_data)

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Guardian {i} setup successful!")
                print(f"   Status: {result['status']}")
            else:
                print(f"❌ Guardian {i} setup failed: {response.status_code}")
                print(f"   Message: {response.text}")

        except Exception as e:
            print(f"❌ Guardian {i} setup error: {e}")

    print(f"\n📊 Summary:")
    print(f"   Total guardians set up: {len(guardians_info)}")
    print(f"   Each guardian keeps their private key and polynomial locally")
    print(f"   Server only received public keys and generated election structures")


if __name__ == "__main__":
    print("🔐 Testing New Guardian Setup System")
    print("="*50)
    print("In this new system:")
    print("1. Guardian generates private key, public key, and polynomial locally")
    print("2. Guardian sends ONLY public key to server")
    print("3. Server generates election structures using public key")
    print("4. Private key and polynomial remain with guardian")
    print("="*50)

    # Test single guardian
    success = test_setup_guardian_endpoint()

    if success:
        # Test multiple guardians
        test_multiple_guardians()

    print("\n🏁 Test completed!")
