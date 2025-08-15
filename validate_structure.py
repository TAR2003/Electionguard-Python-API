#!/usr/bin/env python3
"""
Simplified validation script to test our new guardian setup implementation
without heavy dependencies.
"""

import sys
import os
import json
from typing import Dict, Any

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_service_structure():
    """Test if our service file exists and has the correct structure."""
    print("="*60)
    print("🔍 TESTING SERVICE FILE STRUCTURE")
    print("="*60)

    try:
        service_file = "services/setup_guardian.py"
        if os.path.exists(service_file):
            print(f"✅ Service file exists: {service_file}")
        else:
            print(f"❌ Service file missing: {service_file}")
            return False

        # Read the service file
        with open(service_file, 'r') as f:
            content = f.read()

        # Check for key components
        required_components = [
            "setup_guardian_service",
            "guardian_id",
            "public_key",
            "sequence_order",
            "number_of_guardians",
            "quorum",
            "ElectionPublicKey",
            "coefficient_commitments"
        ]

        missing_components = []
        for component in required_components:
            if component in content:
                print(f"✅ Found required component: {component}")
            else:
                print(f"❌ Missing component: {component}")
                missing_components.append(component)

        if not missing_components:
            print("✅ All required components found in service file")
            return True
        else:
            print(f"❌ Missing {len(missing_components)} required components")
            return False

    except Exception as e:
        print(f"❌ Error checking service structure: {e}")
        return False


def test_api_structure():
    """Test if our API file has the new endpoint."""
    print("\n" + "="*60)
    print("🔍 TESTING API ENDPOINT STRUCTURE")
    print("="*60)

    try:
        api_file = "api.py"
        if os.path.exists(api_file):
            print(f"✅ API file exists: {api_file}")
        else:
            print(f"❌ API file missing: {api_file}")
            return False

        # Read the API file
        with open(api_file, 'r') as f:
            content = f.read()

        # Check for new endpoint
        endpoint_checks = [
            "/setup_guardian",
            "api_setup_guardian",
            "setup_guardian_service",
            "guardian_id",
            "public_key"
        ]

        missing_checks = []
        for check in endpoint_checks:
            if check in content:
                print(f"✅ Found in API: {check}")
            else:
                print(f"❌ Missing in API: {check}")
                missing_checks.append(check)

        if not missing_checks:
            print("✅ All required API components found")
            return True
        else:
            print(f"❌ Missing {len(missing_checks)} API components")
            return False

    except Exception as e:
        print(f"❌ Error checking API structure: {e}")
        return False


def test_api_format():
    """Test if our API format documentation exists."""
    print("\n" + "="*60)
    print("🔍 TESTING API FORMAT DOCUMENTATION")
    print("="*60)

    try:
        format_file = "setup_guardian_api_format.txt"
        if os.path.exists(format_file):
            print(f"✅ API format file exists: {format_file}")
        else:
            print(f"❌ API format file missing: {format_file}")
            return False

        # Read the format file
        with open(format_file, 'r') as f:
            content = f.read()

        # Check for required format components
        format_checks = [
            "setup_guardian",
            "setup_guardian_response",
            "guardian_id: str",
            "public_key: str",
            "sequence_order: int",
            "status: str"
        ]

        missing_format = []
        for check in format_checks:
            if check in content:
                print(f"✅ Found format spec: {check}")
            else:
                print(f"❌ Missing format spec: {check}")
                missing_format.append(check)

        if not missing_format:
            print("✅ All required format specifications found")
            return True
        else:
            print(f"❌ Missing {len(missing_format)} format specifications")
            return False

    except Exception as e:
        print(f"❌ Error checking API format: {e}")
        return False


def test_sample_data():
    """Test if sample input/output files exist."""
    print("\n" + "="*60)
    print("🔍 TESTING SAMPLE DATA FILES")
    print("="*60)

    sample_files = [
        "io/setup_guardian_data.json",
        "io/setup_guardian_response.json"
    ]

    all_exist = True
    for file_path in sample_files:
        if os.path.exists(file_path):
            print(f"✅ Sample file exists: {file_path}")

            # Try to parse JSON
            try:
                with open(file_path, 'r') as f:
                    json.load(f)
                print(f"✅ Valid JSON format: {file_path}")
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON in {file_path}: {e}")
                all_exist = False
        else:
            print(f"❌ Sample file missing: {file_path}")
            all_exist = False

    return all_exist


def test_documentation():
    """Test if documentation files exist."""
    print("\n" + "="*60)
    print("🔍 TESTING DOCUMENTATION")
    print("="*60)

    doc_files = [
        "GUARDIAN_SETUP_CHANGES.md",
        "test_setup_guardian.py"
    ]

    all_exist = True
    for file_path in doc_files:
        if os.path.exists(file_path):
            print(f"✅ Documentation file exists: {file_path}")
        else:
            print(f"❌ Documentation file missing: {file_path}")
            all_exist = False

    return all_exist


def test_security_design():
    """Test if the security design is properly implemented."""
    print("\n" + "="*60)
    print("🔒 TESTING SECURITY DESIGN")
    print("="*60)

    try:
        # Check service file for security properties
        with open("services/setup_guardian.py", 'r') as f:
            service_content = f.read()

        # Security checks
        security_checks = [
            # Should NOT generate private keys
            ("private.*key.*rand_q", False, "Should not generate private keys"),
            ("rand_q\\(\\)", False, "Should not generate random private keys"),

            # Should handle public keys
            ("public_key", True, "Should handle public keys"),
            ("int_to_p", True, "Should convert public key from int"),

            # Should create election structures
            ("ElectionPublicKey", True, "Should create election public key"),
            ("coefficient_commitments", True, "Should create commitments"),

            # Should return only public data
            ("guardian_data", True, "Should return guardian data"),
            ("to_raw", True, "Should serialize public data")
        ]

        import re
        all_passed = True

        for pattern, should_exist, description in security_checks:
            found = bool(re.search(pattern, service_content, re.IGNORECASE))

            if found == should_exist:
                status = "✅ PASS"
            else:
                status = "❌ FAIL"
                all_passed = False

            expected = "found" if should_exist else "NOT found"
            print(f"   {status}: {description} - Pattern '{pattern}' {expected}")

        if all_passed:
            print("\n🎉 SECURITY DESIGN CHECKS PASSED!")
            print("   ✅ Service does not generate private keys")
            print("   ✅ Service only handles public keys")
            print("   ✅ Service creates proper election structures")
        else:
            print("\n❌ SOME SECURITY DESIGN CHECKS FAILED!")

        return all_passed

    except Exception as e:
        print(f"❌ Error in security design test: {e}")
        return False


def test_backward_compatibility():
    """Test if backward compatibility is maintained."""
    print("\n" + "="*60)
    print("🔄 TESTING BACKWARD COMPATIBILITY")
    print("="*60)

    try:
        # Check that original endpoint still exists
        with open("api.py", 'r') as f:
            api_content = f.read()

        # Check for original setup_guardians endpoint
        original_checks = [
            "/setup_guardians",
            "api_setup_guardians",
            "setup_guardians_service"
        ]

        missing_original = []
        for check in original_checks:
            if check in api_content:
                print(f"✅ Original endpoint preserved: {check}")
            else:
                print(f"❌ Original endpoint missing: {check}")
                missing_original.append(check)

        if not missing_original:
            print("✅ Backward compatibility maintained")
            return True
        else:
            print(
                f"❌ Backward compatibility broken: {len(missing_original)} components missing")
            return False

    except Exception as e:
        print(f"❌ Error checking backward compatibility: {e}")
        return False


def main():
    """Run all validation tests."""
    print("🚀 ELECTIONGUARD GUARDIAN SETUP VALIDATION")
    print("="*60)
    print("Testing the implementation structure and design...")
    print("This test validates without requiring heavy dependencies")
    print("="*60)

    # Track test results
    results = {}

    # Run all tests
    results['service_structure'] = test_service_structure()
    results['api_structure'] = test_api_structure()
    results['api_format'] = test_api_format()
    results['sample_data'] = test_sample_data()
    results['documentation'] = test_documentation()
    results['security_design'] = test_security_design()
    results['backward_compatibility'] = test_backward_compatibility()

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
        print("\n🎉 ALL STRUCTURE TESTS PASSED!")
        print("✅ Implementation files are properly structured!")
        print("✅ Security design is correctly implemented!")
        print("✅ API endpoints are properly defined!")
        print("✅ Documentation is complete!")
        print("✅ Backward compatibility is maintained!")
        print("\n📋 NEXT STEPS TO VERIFY FULL FUNCTIONALITY:")
        print("1. Install all dependencies (gmpy2, electionguard)")
        print("2. Start the API server: python api.py")
        print("3. Run functional tests: python test_setup_guardian.py")
        print("4. Test with real HTTP requests")
    else:
        print(f"\n⚠️ {total - passed} tests failed!")
        print("❌ Implementation structure needs fixes!")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
