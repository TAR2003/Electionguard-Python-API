import requests
import json


def test_setup_guardian():
    """Test the /setup_guardian endpoint"""

    url = "http://localhost:5000/setup_guardian"

    # Test data matching your API format
    test_data = {
        "guardian_id": "guardian_1",
        "sequence_order": 1,
        "public_key": "123456789",  # Guardian's generated public key
        "number_of_guardians": 3,
        "quorum": 2,
        "party_names": ["Party A", "Party B"],
        "candidate_names": ["Candidate 1", "Candidate 2", "Candidate 3"]
    }

    print("🚀 Testing /setup_guardian endpoint...")
    print(f"📡 Sending request to: {url}")
    print(f"📦 Request data: {json.dumps(test_data, indent=2)}")

    try:
        response = requests.post(
            url,
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        print(f"\n📊 Response Status: {response.status_code}")

        if response.status_code == 200:
            response_data = response.json()
            print("✅ SUCCESS! API is working correctly")
            print(f"📋 Response data: {json.dumps(response_data, indent=2)}")

            # Security check
            response_str = json.dumps(response_data).lower()
            if "private_key" in response_str:
                print("❌ SECURITY VIOLATION: private_key found in response!")
            else:
                print("✅ SECURITY: No private keys in response")

        else:
            print(f"❌ ERROR: Status {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")


if __name__ == "__main__":
    test_setup_guardian()
