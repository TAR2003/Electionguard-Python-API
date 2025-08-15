#!/usr/bin/env python3
"""
Simple validation script to test our new guardian setup implementation
without requiring the full API server to be running.
"""

import sys
import os
import json
from typing import Dict, Any

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_import_modules():
    """Test if our modules can be imported correctly."""
    print("="*60)
    print("🔍 TESTING MODULE IMPORTS")
    print("="*60)

    try:
        # Test basic electionguard imports
        from electionguard.group import g_pow_p, rand_q, int_to_p, int_to_q
        print("✅ electionguard.group imported successfully")

        from electionguard.election_polynomial import generate_polynomial
        print("✅ electionguard.election_polynomial imported successfully")

        from electionguard.serialize import to_raw, from_raw
        print("✅ electionguard.serialize imported successfully")

        from electionguard.key_ceremony import ElectionPublicKey
        print("✅ electionguard.key_ceremony imported successfully")

        # Test our new service
        from services.setup_guardian import setup_guardian_service
        print("✅ services.setup_guardian imported successfully")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_key_generation():
    """Test the guardian key generation process."""
    print("\n" + "="*60)
    print("🔐 TESTING KEY GENERATION")
    print("="*60)

    try:
        from electionguard.group import g_pow_p, rand_q

        # Generate guardian keys (what guardian does locally)
        print("🔑 Generating guardian keys locally...")
        private_key = rand_q()
        public_key = g_pow_p(private_key)

        print(f"✅ Private key generated: {str(int(private_key))[:20]}...")
        print(f"✅ Public key generated: {str(int(public_key))[:20]}...")

        return {
            'private_key': private_key,
            'public_key': public_key
        }

    except Exception as e:
        print(f"❌ Key generation error: {e}")
        return None


def test_guardian_service():
    """Test our new guardian setup service."""
    print("\n" + "="*60)
    print("🛠️ TESTING GUARDIAN SETUP SERVICE")
    print("="*60)

    try:
        from services.setup_guardian import setup_guardian_service
        from electionguard.group import g_pow_p, rand_q

        # Generate test keys
        private_key = rand_q()
        public_key = g_pow_p(private_key)

        # Test the service with guardian's public key only
        print("📤 Calling setup_guardian_service with public key only...")

        result = setup_guardian_service(
            guardian_id="test_guardian_1",
            sequence_order=1,
            public_key=str(int(public_key)),  # Only public key sent
            number_of_guardians=3,
            quorum=3,
            party_names=["Democratic Party", "Republican Party"],
            candidate_names=["Alice Johnson", "Bob Smith"]
        )

        print("✅ Service call successful!")
        print(f"✅ Guardian ID: {result['guardian_id']}")
        print(f"✅ Sequence Order: {result['sequence_order']}")
        print(f"✅ Number of Guardians: {result['number_of_guardians']}")
        print(f"✅ Quorum: {result['quorum']}")

        # Check that private key is NOT in the response
        response_str = json.dumps(result)
        private_key_str = str(int(private_key))

        if private_key_str not in response_str:
            print("✅ SECURITY CHECK PASSED: Private key NOT found in response")
        else:
            print("❌ SECURITY CHECK FAILED: Private key found in response!")
            return False

        # Check that public key IS in the response
        public_key_str = str(int(public_key))
        if public_key_str in response_str:
            print("✅ PUBLIC KEY CHECK PASSED: Public key found in response")
        else:
            print("❌ PUBLIC KEY CHECK FAILED: Public key not found in response!")
            return False

        return result

    except Exception as e:
        print(f"❌ Guardian service error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_multiple_guardians():
    """Test setting up multiple guardians."""
    print("\n" + "="*60)
    print("👥 TESTING MULTIPLE GUARDIAN SETUP")
    print("="*60)

    try:
        from services.setup_guardian import setup_guardian_service
        from electionguard.group import g_pow_p, rand_q

        guardians_data = []

        for i in range(1, 4):  # 3 guardians
            print(f"\n--- Setting up Guardian {i} ---")

            # Each guardian generates their own keys
            private_key = rand_q()
            public_key = g_pow_p(private_key)

            # Guardian keeps private key locally
            guardian_local_data = {
                'guardian_id': f'guardian_{i}',
                'private_key': private_key,  # This stays local
                'public_key': public_key
            }

            # Guardian sends only public key to server
            result = setup_guardian_service(
                guardian_id=f'guardian_{i}',
                sequence_order=i,
                public_key=str(int(public_key)),  # Only this is sent
                number_of_guardians=3,
                quorum=3,
                party_names=["Democratic Party", "Republican Party"],
                candidate_names=["Alice Johnson", "Bob Smith"]
            )

            print(f"✅ Guardian {i} setup successful")
            guardians_data.append({
                'local_data': guardian_local_data,
                'server_response': result
            })

        print(f"\n📊 SUMMARY:")
        print(f"✅ Successfully set up {len(guardians_data)} guardians")
        print(f"✅ Each guardian keeps private key locally")
        print(f"✅ Server only received public keys")

        return guardians_data

    except Exception as e:
        print(f"❌ Multiple guardians test error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_security_properties():
    """Test security properties of the new system."""
    print("\n" + "="*60)
    print("🔒 TESTING SECURITY PROPERTIES")
    print("="*60)

    try:
        from services.setup_guardian import setup_guardian_service
        from electionguard.group import g_pow_p, rand_q
        from electionguard.election_polynomial import generate_polynomial

        # Simulate guardian generating keys locally
        private_key = rand_q()
        public_key = g_pow_p(private_key)
        polynomial = generate_polynomial(3)  # Guardian keeps this secret

        print("🔐 Guardian generated secrets locally:")
        print(f"   Private key: {str(int(private_key))[:20]}... (KEPT LOCAL)")
        print(
            f"   Public key: {str(int(public_key))[:20]}... (SENT TO SERVER)")
        print(f"   Polynomial: [secret] (KEPT LOCAL)")

        # Call service with only public key
        result = setup_guardian_service(
            guardian_id="security_test_guardian",
            sequence_order=1,
            public_key=str(int(public_key)),
            number_of_guardians=3,
            quorum=3,
            party_names=["Party A", "Party B"],
            candidate_names=["Alice", "Bob"]
        )

        print("\n🌐 Server response analysis:")

        # Convert result to string for searching
        result_str = json.dumps(result, default=str)

        # Security checks
        checks = [
            ("Private key", str(int(private_key)), False),
            ("Public key", str(int(public_key)), True),
            ("Guardian ID", "security_test_guardian", True),
            ("Sequence order", "1", True)
        ]

        all_passed = True
        for check_name, search_value, should_exist in checks:
            exists = search_value in result_str
            if exists == should_exist:
                status = "✅ PASS"
            else:
                status = "❌ FAIL"
                all_passed = False

            expected = "should be present" if should_exist else "should NOT be present"
            print(f"   {status}: {check_name} {expected}")

        if all_passed:
            print("\n🎉 ALL SECURITY CHECKS PASSED!")
            print("   ✅ Private keys remain with guardian")
            print("   ✅ Only public information transmitted")
            print("   ✅ Server cannot access secrets")
        else:
            print("\n❌ SOME SECURITY CHECKS FAILED!")

        return all_passed

    except Exception as e:
        print(f"❌ Security test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""
    print("🚀 ELECTIONGUARD GUARDIAN SETUP VALIDATION")
    print("="*60)
    print("Testing the new guardian setup implementation...")
    print("Guardian generates keys locally, sends only public key to server")
    print("="*60)

    # Track test results
    results = {}

    # Test 1: Module imports
    results['imports'] = test_import_modules()

    if not results['imports']:
        print("\n❌ CRITICAL: Module imports failed. Cannot continue tests.")
        return False

    # Test 2: Key generation
    key_result = test_key_generation()
    results['key_generation'] = key_result is not None

    # Test 3: Guardian service
    service_result = test_guardian_service()
    results['guardian_service'] = service_result is not None

    # Test 4: Multiple guardians
    multiple_result = test_multiple_guardians()
    results['multiple_guardians'] = multiple_result is not None

    # Test 5: Security properties
    results['security'] = test_security_properties()

    # Summary
    print("\n" + "="*60)
    print("📋 VALIDATION SUMMARY")
    print("="*60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"{status}: {test_name.replace('_', ' ').title()}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ The new guardian setup implementation is working correctly!")
        print("✅ Security properties are maintained!")
        print("✅ Private keys and polynomials remain with guardians!")
    else:
        print(f"\n⚠️ {total - passed} tests failed!")
        print("❌ Implementation needs fixes before deployment!")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
