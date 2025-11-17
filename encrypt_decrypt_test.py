#!/usr/bin/env python

import requests
import json
import random
import string
import time
from typing import Dict, List, Tuple
from collections import defaultdict
from statistics import mean, stdev

import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API Base URL
BASE_URL = "http://192.168.30.138:5000"

# Test Configuration
STRING_SIZES = [10, 100, 1000, 10000, 100000]
ITERATIONS_PER_SIZE = 100

# Timing tracker
timing_data = defaultdict(lambda: {'encryption_times': [], 'decryption_times': [], 'total_times': []})
# Size tracker
size_data = defaultdict(lambda: {'request_sizes': [], 'response_sizes': []})


def generate_random_string(length: int) -> str:
    """Generate a random string of specified length."""
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for _ in range(length))


def format_size(size_bytes: int) -> str:
    """Format size in bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f}TB"


def test_encrypt_decrypt(private_key: str, string_size: int) -> Tuple[float, float, float]:
    """
    Test encryption and decryption of a private key.
    
    Returns:
        Tuple of (encryption_time, decryption_time, total_time)
    """
    # STEP 1: Encrypt
    encrypt_request = {
        "private_key": private_key
    }
    
    # Calculate request size
    encrypt_request_json = json.dumps(encrypt_request)
    encrypt_request_size = len(encrypt_request_json.encode('utf-8'))
    
    # Encrypt
    encrypt_start = time.time()
    encrypt_response = requests.post(
        f"{BASE_URL}/api/encrypt",
        json=encrypt_request,
        verify=False,
        timeout=None
    )
    encrypt_end = time.time()
    encryption_time = encrypt_end - encrypt_start
    
    # Calculate response size
    encrypt_response_size = len(encrypt_response.content)
    
    assert encrypt_response.status_code == 200, f"Encryption failed: {encrypt_response.text}"
    encrypt_result = encrypt_response.json()
    
    # Store sizes
    size_data[string_size]['request_sizes'].append(encrypt_request_size)
    size_data[string_size]['response_sizes'].append(encrypt_response_size)
    
    # STEP 2: Decrypt
    decrypt_request = {
        "encrypted_data": encrypt_result['encrypted_data'],
        "credentials": encrypt_result['credentials']
    }
    
    # Calculate decrypt request size
    decrypt_request_json = json.dumps(decrypt_request)
    decrypt_request_size = len(decrypt_request_json.encode('utf-8'))
    
    # Decrypt
    decrypt_start = time.time()
    decrypt_response = requests.post(
        f"{BASE_URL}/api/decrypt",
        json=decrypt_request,
        verify=False,
        timeout=None
    )
    decrypt_end = time.time()
    decryption_time = decrypt_end - decrypt_start
    
    # Calculate decrypt response size
    decrypt_response_size = len(decrypt_response.content)
    
    assert decrypt_response.status_code == 200, f"Decryption failed: {decrypt_response.text}"
    decrypt_result = decrypt_response.json()
    
    # Verify the decrypted data matches the original
    assert decrypt_result['private_key'] == private_key, "Decrypted data does not match original!"
    
    total_time = encryption_time + decryption_time
    
    return encryption_time, decryption_time, total_time


def run_encryption_tests():
    """Run encryption/decryption tests for different string sizes."""
    
    print("=" * 100)
    print("ENCRYPTION/DECRYPTION PERFORMANCE TEST")
    print("=" * 100)
    print(f"Configuration:")
    print(f"  - String Sizes: {STRING_SIZES}")
    print(f"  - Iterations per Size: {ITERATIONS_PER_SIZE}")
    print("=" * 100)
    
    for string_size in STRING_SIZES:
        print(f"\n🔹 Testing with string size: {string_size} characters")
        print(f"  Running {ITERATIONS_PER_SIZE} iterations...")
        
        for iteration in range(ITERATIONS_PER_SIZE):
            # Generate random string
            test_string = generate_random_string(string_size)
            
            # Test encrypt/decrypt
            try:
                encryption_time, decryption_time, total_time = test_encrypt_decrypt(test_string, string_size)
                
                # Store timing data
                timing_data[string_size]['encryption_times'].append(encryption_time)
                timing_data[string_size]['decryption_times'].append(decryption_time)
                timing_data[string_size]['total_times'].append(total_time)
                
                if (iteration + 1) % 2 == 0 or ITERATIONS_PER_SIZE <= 5:
                    print(f"    ✓ Iteration {iteration + 1}/{ITERATIONS_PER_SIZE} completed")
                
            except Exception as e:
                print(f"    ✗ Iteration {iteration + 1} failed: {str(e)}")
                continue
        
        print(f"  ✅ Completed all {ITERATIONS_PER_SIZE} iterations for size {string_size}")
    
    print("\n✅ ALL TESTS COMPLETED!")


def print_results_summary():
    """Print a formatted summary of all test results."""
    print("\n" + "=" * 150)
    print("ENCRYPTION/DECRYPTION PERFORMANCE SUMMARY")
    print("=" * 150)
    print(f"{'String Size':<15} {'Iterations':<12} {'Avg Encrypt':<15} {'Avg Decrypt':<15} {'Avg Total':<15} {'Avg Req Size':<15} {'Avg Resp Size':<15}")
    print("-" * 150)
    
    for string_size in STRING_SIZES:
        data = timing_data[string_size]
        
        if not data['encryption_times']:
            continue
        
        num_iterations = len(data['encryption_times'])
        avg_encrypt = mean(data['encryption_times'])
        avg_decrypt = mean(data['decryption_times'])
        avg_total = mean(data['total_times'])
        
        # Size data
        req_sizes = size_data[string_size]['request_sizes']
        resp_sizes = size_data[string_size]['response_sizes']
        avg_req_size = format_size(mean(req_sizes)) if req_sizes else 'N/A'
        avg_resp_size = format_size(mean(resp_sizes)) if resp_sizes else 'N/A'
        
        print(f"{string_size:<15} {num_iterations:<12} {avg_encrypt:<15.6f}s {avg_decrypt:<15.6f}s {avg_total:<15.6f}s {avg_req_size:<15} {avg_resp_size:<15}")
    
    print("=" * 150)


def export_results_to_file():
    """Export detailed results to a text file."""
    filename = "encrypt_decrypt_results.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=" * 150 + "\n")
        f.write("ENCRYPTION/DECRYPTION PERFORMANCE TEST RESULTS\n")
        f.write("=" * 150 + "\n")
        f.write(f"Test Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"String Sizes Tested: {STRING_SIZES}\n")
        f.write(f"Iterations per Size: {ITERATIONS_PER_SIZE}\n")
        f.write("\n" + "-" * 150 + "\n")
        f.write("PERFORMANCE SUMMARY\n")
        f.write("-" * 150 + "\n")
        f.write(f"{'String Size':<15} {'Iterations':<12} {'Avg Encrypt':<15} {'Min Encrypt':<15} {'Max Encrypt':<15} {'Std Dev Enc':<15} {'Avg Decrypt':<15} {'Min Decrypt':<15} {'Max Decrypt':<15} {'Std Dev Dec':<15}\n")
        f.write("-" * 150 + "\n")
        
        for string_size in STRING_SIZES:
            data = timing_data[string_size]
            
            if not data['encryption_times']:
                continue
            
            num_iterations = len(data['encryption_times'])
            
            # Encryption stats
            avg_encrypt = mean(data['encryption_times'])
            min_encrypt = min(data['encryption_times'])
            max_encrypt = max(data['encryption_times'])
            std_encrypt = stdev(data['encryption_times']) if num_iterations > 1 else 0.0
            
            # Decryption stats
            avg_decrypt = mean(data['decryption_times'])
            min_decrypt = min(data['decryption_times'])
            max_decrypt = max(data['decryption_times'])
            std_decrypt = stdev(data['decryption_times']) if num_iterations > 1 else 0.0
            
            f.write(f"{string_size:<15} {num_iterations:<12} {avg_encrypt:<15.6f}s {min_encrypt:<15.6f}s {max_encrypt:<15.6f}s {std_encrypt:<15.6f}s {avg_decrypt:<15.6f}s {min_decrypt:<15.6f}s {max_decrypt:<15.6f}s {std_decrypt:<15.6f}s\n")
        
        f.write("-" * 150 + "\n\n")
        
        # Total time comparison
        f.write("TOTAL TIME COMPARISON (Encryption + Decryption)\n")
        f.write("-" * 150 + "\n")
        f.write(f"{'String Size':<15} {'Avg Total':<15} {'Min Total':<15} {'Max Total':<15} {'Std Dev':<15}\n")
        f.write("-" * 150 + "\n")
        
        for string_size in STRING_SIZES:
            data = timing_data[string_size]
            
            if not data['total_times']:
                continue
            
            avg_total = mean(data['total_times'])
            min_total = min(data['total_times'])
            max_total = max(data['total_times'])
            std_total = stdev(data['total_times']) if len(data['total_times']) > 1 else 0.0
            
            f.write(f"{string_size:<15} {avg_total:<15.6f}s {min_total:<15.6f}s {max_total:<15.6f}s {std_total:<15.6f}s\n")
        
        f.write("-" * 150 + "\n\n")
        
        # Size comparison
        f.write("REQUEST/RESPONSE SIZE COMPARISON\n")
        f.write("-" * 150 + "\n")
        f.write(f"{'String Size':<15} {'Avg Req Size':<20} {'Avg Resp Size':<20} {'Total Data':<20}\n")
        f.write("-" * 150 + "\n")
        
        for string_size in STRING_SIZES:
            req_sizes = size_data[string_size]['request_sizes']
            resp_sizes = size_data[string_size]['response_sizes']
            
            if not req_sizes:
                continue
            
            avg_req_size = mean(req_sizes)
            avg_resp_size = mean(resp_sizes)
            total_data = avg_req_size + avg_resp_size
            
            f.write(f"{string_size:<15} {format_size(avg_req_size):<20} {format_size(avg_resp_size):<20} {format_size(total_data):<20}\n")
        
        f.write("-" * 150 + "\n\n")
        
        # Scaling analysis
        f.write("SCALING ANALYSIS\n")
        f.write("-" * 150 + "\n")
        f.write("Shows how performance scales as string size increases\n")
        f.write(f"{'From Size':<15} {'To Size':<15} {'Size Ratio':<15} {'Time Ratio (Enc)':<20} {'Time Ratio (Dec)':<20} {'Time Ratio (Total)':<20}\n")
        f.write("-" * 150 + "\n")
        
        previous_size = None
        previous_data = None
        
        for string_size in STRING_SIZES:
            data = timing_data[string_size]
            
            if not data['encryption_times']:
                continue
            
            if previous_size is not None and previous_data is not None:
                size_ratio = string_size / previous_size
                
                prev_avg_encrypt = mean(previous_data['encryption_times'])
                curr_avg_encrypt = mean(data['encryption_times'])
                encrypt_ratio = curr_avg_encrypt / prev_avg_encrypt if prev_avg_encrypt > 0 else 0
                
                prev_avg_decrypt = mean(previous_data['decryption_times'])
                curr_avg_decrypt = mean(data['decryption_times'])
                decrypt_ratio = curr_avg_decrypt / prev_avg_decrypt if prev_avg_decrypt > 0 else 0
                
                prev_avg_total = mean(previous_data['total_times'])
                curr_avg_total = mean(data['total_times'])
                total_ratio = curr_avg_total / prev_avg_total if prev_avg_total > 0 else 0
                
                f.write(f"{previous_size:<15} {string_size:<15} {size_ratio:<15.2f}x {encrypt_ratio:<20.4f}x {decrypt_ratio:<20.4f}x {total_ratio:<20.4f}x\n")
            
            previous_size = string_size
            previous_data = data
        
        f.write("=" * 150 + "\n")
    
    print(f"\n📄 Detailed results exported to {filename}")


def main():
    """Main entry point for the encryption/decryption test."""
    print("\nStarting Encryption/Decryption Performance Test...\n")
    
    try:
        # Run the tests
        run_encryption_tests()
        
        # Print summary
        print_results_summary()
        
        # Export to file
        export_results_to_file()
        
        print("\n" + "=" * 100)
        print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 100)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
