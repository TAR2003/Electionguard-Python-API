#!/usr/bin/env python3
"""
Simple test to check if the API server can start and respond.
"""

import requests
import json
import time
import subprocess
import sys
from threading import Thread
import os


def start_api_server():
    """Start the API server in a subprocess"""
    try:
        # Change to the correct directory
        os.chdir(r"e:\assignment\Electionguard-Python-API")

        # Start the server
        process = subprocess.Popen(
            [sys.executable, "api.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        return process
    except Exception as e:
        print(f"❌ Failed to start API server: {e}")
        return None


def test_endpoints():
    """Test the API endpoints"""
    base_url = "http://localhost:5000"

    # Wait for server to start
    print("⏳ Waiting for server to start...")
    for i in range(30):  # Wait up to 30 seconds
        try:
            response = requests.get(f"{base_url}/health", timeout=2)
            if response.status_code == 200:
                print("✅ Server is running!")
                break
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
    else:
        print("❌ Server failed to start within 30 seconds")
        return False

    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Health check: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")

    # Test setup_guardian endpoint
    test_data = {
        "guardian_id": "test_guardian_1",
        "sequence_order": 1,
        "public_key": "123456789012345678901234567890",
        "number_of_guardians": 3,
        "quorum": 2,
        "party_names": ["Party A", "Party B"],
        "candidate_names": ["Alice", "Bob", "Charlie"]
    }

    try:
        print("\n🚀 Testing /setup_guardian endpoint...")
        response = requests.post(
            f"{base_url}/setup_guardian",
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            print("✅ SUCCESS! /setup_guardian endpoint is working")
            response_data = response.json()
            print("Response keys:", list(response_data.keys()))

            # Check that response has required fields
            required_fields = ["status", "guardian_id",
                               "sequence_order", "guardian_data", "election_public_key"]
            missing_fields = [
                field for field in required_fields if field not in response_data]

            if missing_fields:
                print(f"⚠️  Missing fields in response: {missing_fields}")
            else:
                print("✅ All required fields present in response")

            # Security check: ensure no private keys
            response_str = json.dumps(response_data).lower()
            if "private_key" in response_str:
                print("❌ SECURITY VIOLATION: private_key found in response!")
            else:
                print("✅ SECURITY: No private keys in response")

        elif response.status_code == 404:
            print("❌ ERROR: Endpoint not found (404)")
            print("This means the /setup_guardian route is not properly registered")
        else:
            print(f"❌ ERROR: Status {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

    return True


def main():
    """Main test function"""
    print("🧪 Testing ElectionGuard API - setup_guardian endpoint")
    print("=" * 60)

    # Start the API server
    server_process = start_api_server()

    if not server_process:
        print("❌ Failed to start server")
        return

    try:
        # Test the endpoints
        success = test_endpoints()

        if success:
            print("\n🎉 API test completed successfully!")
        else:
            print("\n❌ API test failed")

    finally:
        # Clean up
        print("\n🛑 Stopping server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
        print("✅ Server stopped")


if __name__ == "__main__":
    main()
