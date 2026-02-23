#!/usr/bin/env python

"""
Ballot Encryption Load Testing Framework
========================================
Professional load testing suite for the create_encrypted_ballot API endpoint
using concurrent threading to simulate real-world election scenarios.

Metrics Collected:
- Throughput (requests/second)
- Response Time (mean, median, p95, p99)
- Concurrency Performance
- Error Rate
- Resource Utilization Patterns
"""

import requests
import json
import time
import random
import threading
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from statistics import mean, median, stdev
from queue import Queue
import urllib3
from dataclasses import dataclass, field
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_URL = "http://192.168.30.138:5000"

# Load Test Scenarios (concurrent_users, requests_per_user)
LOAD_SCENARIOS = [
    (1, 10),      # Baseline: 1 user, 10 requests
    (5, 10),      # Light Load: 5 concurrent users, 10 requests each (50 total)
    (10, 10),     # Moderate Load: 10 concurrent users, 10 requests each (100 total)
    (20, 10),     # Heavy Load: 20 concurrent users, 10 requests each (200 total)
    (50, 10),     # Stress Test: 50 concurrent users, 10 requests each (500 total)
    (100, 10),    # High Stress: 100 concurrent users, 10 requests each (1000 total)
    (200, 10),    # Extreme Load: 200 concurrent users, 10 requests each (2000 total)
    (500, 10),    # Maximum Load: 500 concurrent users, 10 requests each (5000 total)
    (1000, 10),    # Peak Load: 1000 concurrent users, 10 requests each (10000 total)
    (2000, 10),    # Ultimate Load: 2000 concurrent users, 10 requests each (20000 total)
    (5000, 10)     # Epic Load: 5000 concurrent users, 10 requests each (50000 total)
    
]

# Election Configuration (matches test-api.py setup)
NUMBER_OF_GUARDIANS = 5
QUORUM = 3
PARTY_NAMES = [
    "Democratic Alliance",
    "Progressive Coalition",
    "Unity Party",
    "Reform League"
]
CANDIDATE_NAMES = [
    "Alice Johnson",
    "Bob Smith",
    "Carol White",
    "David Brown"
]

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class RequestMetrics:
    """Metrics for a single API request"""
    thread_id: int
    request_number: int
    response_time: float
    status_code: int
    success: bool
    error_message: Optional[str] = None
    request_size: int = 0
    response_size: int = 0
    timestamp: float = 0.0


@dataclass
class LoadTestResult:
    """Aggregated results for a load test scenario"""
    concurrent_users: int
    requests_per_user: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_duration: float
    throughput: float  # requests per second
    mean_response_time: float
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    min_response_time: float
    max_response_time: float
    std_dev_response_time: float
    error_rate: float  # percentage
    mean_request_size: float
    mean_response_size: float
    request_metrics: List[RequestMetrics] = field(default_factory=list)


# ============================================================================
# GLOBAL STATE
# ============================================================================

# Guardian setup data (populated once at start)
guardian_setup_data = {
    'joint_public_key': None,
    'commitment_hash': None,
    'guardians': None
}

# Results storage
load_test_results: List[LoadTestResult] = []

# Thread-safe queue for collecting metrics
metrics_queue = Queue()

# Lock for thread-safe operations
setup_lock = threading.Lock()

# ============================================================================
# SETUP FUNCTIONS
# ============================================================================

def setup_guardians() -> bool:
    """
    Setup guardians once before all load tests.
    This simulates the election initialization phase.
    """
    print("\n" + "=" * 100)
    print("GUARDIAN SETUP (ONE-TIME INITIALIZATION)")
    print("=" * 100)
    
    try:
        request_data = {
            "number_of_guardians": NUMBER_OF_GUARDIANS,
            "quorum": QUORUM,
            "party_names": PARTY_NAMES,
            "candidate_names": CANDIDATE_NAMES
        }
        
        print(f"Setting up {NUMBER_OF_GUARDIANS} guardians with quorum {QUORUM}...")
        start_time = time.time()
        
        response = requests.post(
            f"{BASE_URL}/setup_guardians",
            json=request_data,
            verify=False,
            timeout=300
        )
        
        duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            
            with setup_lock:
                guardian_setup_data['joint_public_key'] = result['joint_public_key']
                guardian_setup_data['commitment_hash'] = result['commitment_hash']
                guardian_setup_data['guardians'] = result
            
            print(f"✅ Guardian setup completed in {duration:.2f}s")
            return True
        else:
            print(f"❌ Guardian setup failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Guardian setup error: {str(e)}")
        return False


# ============================================================================
# LOAD TESTING WORKER FUNCTIONS
# ============================================================================

def encrypt_ballot_worker(
    thread_id: int,
    requests_per_user: int,
    barrier: threading.Barrier
) -> None:
    """
    Worker thread that simulates a single user encrypting multiple ballots.
    
    Args:
        thread_id: Unique identifier for this thread
        requests_per_user: Number of ballots to encrypt
        barrier: Synchronization barrier to ensure all threads start together
    """
    
    # Wait for all threads to be ready
    barrier.wait()
    
    # Simulate different voters choosing different candidates
    for request_num in range(requests_per_user):
        try:
            # Randomly select a candidate (simulates real voter behavior)
            selected_candidate = random.choice(CANDIDATE_NAMES)
            ballot_id = f"ballot-thread{thread_id}-req{request_num}-{int(time.time() * 1000)}"
            
            # Prepare request
            request_data = {
                "party_names": PARTY_NAMES,
                "candidate_names": CANDIDATE_NAMES,
                "candidate_name": selected_candidate,
                "ballot_id": ballot_id,
                "joint_public_key": guardian_setup_data['joint_public_key'],
                "commitment_hash": guardian_setup_data['commitment_hash'],
                "number_of_guardians": NUMBER_OF_GUARDIANS,
                "quorum": QUORUM,
                "ballot_status": "CAST"
            }
            
            request_json = json.dumps(request_data)
            request_size = len(request_json.encode('utf-8'))
            
            # Execute request with timing
            start_time = time.time()
            timestamp = start_time
            
            response = requests.post(
                f"{BASE_URL}/create_encrypted_ballot",
                json=request_data,
                verify=False,
                timeout=300
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            response_size = len(response.content)
            
            # Record metrics
            success = response.status_code == 200
            error_msg = None if success else response.text[:200]
            
            metrics = RequestMetrics(
                thread_id=thread_id,
                request_number=request_num,
                response_time=response_time,
                status_code=response.status_code,
                success=success,
                error_message=error_msg,
                request_size=request_size,
                response_size=response_size,
                timestamp=timestamp
            )
            
            metrics_queue.put(metrics)
            
        except Exception as e:
            # Record error metrics
            metrics = RequestMetrics(
                thread_id=thread_id,
                request_number=request_num,
                response_time=0.0,
                status_code=0,
                success=False,
                error_message=str(e)[:200],
                timestamp=time.time()
            )
            metrics_queue.put(metrics)


def calculate_percentile(sorted_values: List[float], percentile: int) -> float:
    """Calculate the nth percentile from a sorted list of values."""
    if not sorted_values:
        return 0.0
    
    index = (percentile / 100.0) * (len(sorted_values) - 1)
    lower_index = int(index)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    
    if lower_index == upper_index:
        return sorted_values[lower_index]
    
    # Linear interpolation
    fraction = index - lower_index
    return sorted_values[lower_index] + fraction * (sorted_values[upper_index] - sorted_values[lower_index])


def run_load_test_scenario(concurrent_users: int, requests_per_user: int) -> LoadTestResult:
    """
    Execute a single load test scenario with specified concurrency.
    
    Args:
        concurrent_users: Number of concurrent threads (simulated users)
        requests_per_user: Number of requests each user will make
        
    Returns:
        LoadTestResult with aggregated metrics
    """
    print(f"\n{'=' * 100}")
    print(f"LOAD TEST SCENARIO: {concurrent_users} Concurrent Users × {requests_per_user} Requests")
    print(f"Total Expected Requests: {concurrent_users * requests_per_user}")
    print(f"{'=' * 100}")
    
    # Clear metrics queue
    while not metrics_queue.empty():
        metrics_queue.get()
    
    # Create synchronization barrier (ensures all threads start simultaneously)
    barrier = threading.Barrier(concurrent_users)
    
    # Create worker threads
    threads = []
    for thread_id in range(concurrent_users):
        thread = threading.Thread(
            target=encrypt_ballot_worker,
            args=(thread_id, requests_per_user, barrier),
            daemon=True
        )
        threads.append(thread)
    
    # Start all threads and measure total duration
    print(f"Starting {concurrent_users} concurrent threads...")
    start_time = time.time()
    
    for thread in threads:
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    print(f"✅ All threads completed in {total_duration:.2f}s")
    
    # Collect all metrics from queue
    collected_metrics = []
    while not metrics_queue.empty():
        collected_metrics.append(metrics_queue.get())
    
    # Calculate aggregate statistics
    successful_requests = sum(1 for m in collected_metrics if m.success)
    failed_requests = len(collected_metrics) - successful_requests
    
    response_times = [m.response_time for m in collected_metrics if m.success]
    response_times_sorted = sorted(response_times)
    
    if response_times:
        mean_rt = mean(response_times)
        median_rt = median(response_times)
        min_rt = min(response_times)
        max_rt = max(response_times)
        std_rt = stdev(response_times) if len(response_times) > 1 else 0.0
        p95_rt = calculate_percentile(response_times_sorted, 95)
        p99_rt = calculate_percentile(response_times_sorted, 99)
    else:
        mean_rt = median_rt = min_rt = max_rt = std_rt = p95_rt = p99_rt = 0.0
    
    throughput = len(collected_metrics) / total_duration if total_duration > 0 else 0.0
    error_rate = (failed_requests / len(collected_metrics) * 100) if collected_metrics else 0.0
    
    request_sizes = [m.request_size for m in collected_metrics if m.request_size > 0]
    response_sizes = [m.response_size for m in collected_metrics if m.response_size > 0]
    
    mean_req_size = mean(request_sizes) if request_sizes else 0.0
    mean_resp_size = mean(response_sizes) if response_sizes else 0.0
    
    # Print immediate results
    print(f"\nResults Summary:")
    print(f"  Total Requests: {len(collected_metrics)}")
    print(f"  Successful: {successful_requests}")
    print(f"  Failed: {failed_requests}")
    print(f"  Throughput: {throughput:.2f} req/s")
    print(f"  Mean Response Time: {mean_rt:.4f}s")
    print(f"  P95 Response Time: {p95_rt:.4f}s")
    print(f"  Error Rate: {error_rate:.2f}%")
    
    return LoadTestResult(
        concurrent_users=concurrent_users,
        requests_per_user=requests_per_user,
        total_requests=len(collected_metrics),
        successful_requests=successful_requests,
        failed_requests=failed_requests,
        total_duration=total_duration,
        throughput=throughput,
        mean_response_time=mean_rt,
        median_response_time=median_rt,
        p95_response_time=p95_rt,
        p99_response_time=p99_rt,
        min_response_time=min_rt,
        max_response_time=max_rt,
        std_dev_response_time=std_rt,
        error_rate=error_rate,
        mean_request_size=mean_req_size,
        mean_response_size=mean_resp_size,
        request_metrics=collected_metrics
    )


# ============================================================================
# REPORTING FUNCTIONS
# ============================================================================

def print_comprehensive_summary():
    """Print comprehensive summary of all load test results."""
    print("\n" + "=" * 150)
    print("LOAD TEST COMPREHENSIVE SUMMARY")
    print("=" * 150)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Endpoint: {BASE_URL}/create_encrypted_ballot")
    print(f"Election Config: {NUMBER_OF_GUARDIANS} guardians, quorum {QUORUM}, {len(CANDIDATE_NAMES)} candidates")
    print("=" * 150)
    print(f"{'Users':<8} {'Req/User':<10} {'Total Req':<12} {'Success':<10} {'Failed':<10} {'Throughput':<15} {'Mean RT':<12} {'P95 RT':<12} {'P99 RT':<12} {'Error %':<10}")
    print("-" * 150)
    
    for result in load_test_results:
        print(f"{result.concurrent_users:<8} {result.requests_per_user:<10} {result.total_requests:<12} "
              f"{result.successful_requests:<10} {result.failed_requests:<10} "
              f"{result.throughput:<15.2f} {result.mean_response_time:<12.4f}s "
              f"{result.p95_response_time:<12.4f}s {result.p99_response_time:<12.4f}s "
              f"{result.error_rate:<10.2f}")
    
    print("=" * 150)


def export_results_to_file():
    """Export comprehensive load test results to file."""
    filename = "ballot_load_test_results.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=" * 150 + "\n")
        f.write("BALLOT ENCRYPTION LOAD TEST RESULTS\n")
        f.write("=" * 150 + "\n")
        f.write(f"Test Execution Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"API Endpoint: {BASE_URL}/create_encrypted_ballot\n")
        f.write(f"Election Configuration:\n")
        f.write(f"  - Guardians: {NUMBER_OF_GUARDIANS}\n")
        f.write(f"  - Quorum: {QUORUM}\n")
        f.write(f"  - Candidates: {len(CANDIDATE_NAMES)} ({', '.join(CANDIDATE_NAMES)})\n")
        f.write(f"  - Parties: {len(PARTY_NAMES)} ({', '.join(PARTY_NAMES)})\n")
        f.write("\n" + "=" * 150 + "\n")
        f.write("EXECUTIVE SUMMARY\n")
        f.write("=" * 150 + "\n")
        
        # Overall statistics
        total_requests = sum(r.total_requests for r in load_test_results)
        total_successful = sum(r.successful_requests for r in load_test_results)
        total_failed = sum(r.failed_requests for r in load_test_results)
        overall_error_rate = (total_failed / total_requests * 100) if total_requests > 0 else 0.0
        
        f.write(f"Total Requests Executed: {total_requests}\n")
        f.write(f"Total Successful Requests: {total_successful}\n")
        f.write(f"Total Failed Requests: {total_failed}\n")
        f.write(f"Overall Error Rate: {overall_error_rate:.2f}%\n")
        f.write(f"Load Scenarios Tested: {len(load_test_results)}\n")
        
        f.write("\n" + "-" * 150 + "\n")
        f.write("DETAILED PERFORMANCE METRICS\n")
        f.write("-" * 150 + "\n")
        f.write(f"{'Concurrent':<12} {'Requests':<12} {'Total':<10} {'Success':<10} {'Failed':<10} {'Duration':<12} "
                f"{'Throughput':<15} {'Error':<10} {'Mean RT':<12} {'Median RT':<12} {'Min RT':<12} "
                f"{'Max RT':<12} {'Std Dev':<12} {'P95 RT':<12} {'P99 RT':<12}\n")
        f.write(f"{'Users':<12} {'Per User':<12} {'Requests':<10} {'Count':<10} {'Count':<10} {'(seconds)':<12} "
                f"{'(req/sec)':<15} {'Rate %':<10} {'(seconds)':<12} {'(seconds)':<12} {'(seconds)':<12} "
                f"{'(seconds)':<12} {'(seconds)':<12} {'(seconds)':<12} {'(seconds)':<12}\n")
        f.write("-" * 150 + "\n")
        
        for result in load_test_results:
            f.write(f"{result.concurrent_users:<12} {result.requests_per_user:<12} {result.total_requests:<10} "
                   f"{result.successful_requests:<10} {result.failed_requests:<10} {result.total_duration:<12.2f} "
                   f"{result.throughput:<15.2f} {result.error_rate:<10.2f} "
                   f"{result.mean_response_time:<12.6f} {result.median_response_time:<12.6f} "
                   f"{result.min_response_time:<12.6f} {result.max_response_time:<12.6f} "
                   f"{result.std_dev_response_time:<12.6f} {result.p95_response_time:<12.6f} "
                   f"{result.p99_response_time:<12.6f}\n")
        
        f.write("-" * 150 + "\n\n")
        
        # Throughput Analysis
        f.write("THROUGHPUT SCALING ANALYSIS\n")
        f.write("-" * 150 + "\n")
        f.write("Shows how throughput scales with increased concurrent load\n")
        f.write(f"{'Concurrent Users':<20} {'Throughput (req/s)':<25} {'Requests/User/Second':<30} {'Efficiency %':<20}\n")
        f.write("-" * 150 + "\n")
        
        baseline_throughput = load_test_results[0].throughput if load_test_results else 0
        
        for result in load_test_results:
            req_per_user_per_sec = result.throughput / result.concurrent_users if result.concurrent_users > 0 else 0
            ideal_throughput = baseline_throughput * result.concurrent_users
            efficiency = (result.throughput / ideal_throughput * 100) if ideal_throughput > 0 else 0
            
            f.write(f"{result.concurrent_users:<20} {result.throughput:<25.2f} "
                   f"{req_per_user_per_sec:<30.4f} {efficiency:<20.2f}\n")
        
        f.write("-" * 150 + "\n\n")
        
        # Response Time Analysis
        f.write("RESPONSE TIME DEGRADATION ANALYSIS\n")
        f.write("-" * 150 + "\n")
        f.write("Shows how response time degrades under increased load\n")
        f.write(f"{'Concurrent Users':<20} {'Mean RT (s)':<20} {'P95 RT (s)':<20} {'P99 RT (s)':<20} "
                f"{'RT Increase %':<25} {'P95 Increase %':<25}\n")
        f.write("-" * 150 + "\n")
        
        baseline_rt = load_test_results[0].mean_response_time if load_test_results else 0
        baseline_p95 = load_test_results[0].p95_response_time if load_test_results else 0
        
        for result in load_test_results:
            rt_increase = ((result.mean_response_time - baseline_rt) / baseline_rt * 100) if baseline_rt > 0 else 0
            p95_increase = ((result.p95_response_time - baseline_p95) / baseline_p95 * 100) if baseline_p95 > 0 else 0
            
            f.write(f"{result.concurrent_users:<20} {result.mean_response_time:<20.6f} "
                   f"{result.p95_response_time:<20.6f} {result.p99_response_time:<20.6f} "
                   f"{rt_increase:<25.2f} {p95_increase:<25.2f}\n")
        
        f.write("-" * 150 + "\n\n")
        
        # Data Transfer Analysis
        f.write("DATA TRANSFER ANALYSIS\n")
        f.write("-" * 150 + "\n")
        f.write(f"{'Concurrent Users':<20} {'Mean Req Size (KB)':<25} {'Mean Resp Size (KB)':<25} "
                f"{'Total Data/Req (KB)':<25} {'Bandwidth (KB/s)':<25}\n")
        f.write("-" * 150 + "\n")
        
        for result in load_test_results:
            req_size_kb = result.mean_request_size / 1024
            resp_size_kb = result.mean_response_size / 1024
            total_data_kb = req_size_kb + resp_size_kb
            bandwidth = (result.mean_request_size + result.mean_response_size) * result.throughput / 1024
            
            f.write(f"{result.concurrent_users:<20} {req_size_kb:<25.2f} {resp_size_kb:<25.2f} "
                   f"{total_data_kb:<25.2f} {bandwidth:<25.2f}\n")
        
        f.write("-" * 150 + "\n\n")
        
        # Concurrency Analysis
        f.write("CONCURRENCY EFFICIENCY ANALYSIS\n")
        f.write("-" * 150 + "\n")
        f.write("Measures how efficiently the system handles concurrent requests\n")
        f.write(f"{'From Users':<15} {'To Users':<15} {'User Ratio':<15} {'Throughput Ratio':<20} "
                f"{'Mean RT Ratio':<20} {'P95 RT Ratio':<20}\n")
        f.write("-" * 150 + "\n")
        
        for i in range(1, len(load_test_results)):
            prev = load_test_results[i - 1]
            curr = load_test_results[i]
            
            user_ratio = curr.concurrent_users / prev.concurrent_users if prev.concurrent_users > 0 else 0
            throughput_ratio = curr.throughput / prev.throughput if prev.throughput > 0 else 0
            rt_ratio = curr.mean_response_time / prev.mean_response_time if prev.mean_response_time > 0 else 0
            p95_ratio = curr.p95_response_time / prev.p95_response_time if prev.p95_response_time > 0 else 0
            
            f.write(f"{prev.concurrent_users:<15} {curr.concurrent_users:<15} {user_ratio:<15.2f}x "
                   f"{throughput_ratio:<20.4f}x {rt_ratio:<20.4f}x {p95_ratio:<20.4f}x\n")
        
        f.write("-" * 150 + "\n\n")
        
        # Performance Recommendations
        f.write("PERFORMANCE CHARACTERISTICS & OBSERVATIONS\n")
        f.write("-" * 150 + "\n")
        
        if load_test_results:
            max_throughput_result = max(load_test_results, key=lambda r: r.throughput)
            min_error_result = min(load_test_results, key=lambda r: r.error_rate)
            
            f.write(f"Peak Throughput: {max_throughput_result.throughput:.2f} req/s ")
            f.write(f"at {max_throughput_result.concurrent_users} concurrent users\n")
            
            f.write(f"Lowest Error Rate: {min_error_result.error_rate:.2f}% ")
            f.write(f"at {min_error_result.concurrent_users} concurrent users\n")
            
            # Calculate if system is scaling linearly
            if len(load_test_results) >= 2:
                linear_scaling = True
                for i in range(1, len(load_test_results)):
                    prev = load_test_results[i - 1]
                    curr = load_test_results[i]
                    user_ratio = curr.concurrent_users / prev.concurrent_users
                    throughput_ratio = curr.throughput / prev.throughput
                    
                    if throughput_ratio < user_ratio * 0.7:  # Less than 70% of ideal scaling
                        linear_scaling = False
                        f.write(f"\nScaling Bottleneck Detected: ")
                        f.write(f"From {prev.concurrent_users} to {curr.concurrent_users} users, ")
                        f.write(f"throughput only increased {throughput_ratio:.2f}x (expected {user_ratio:.2f}x)\n")
                
                if linear_scaling:
                    f.write("\nSystem demonstrates near-linear scaling characteristics across tested load ranges.\n")
            
            # Check for concerning error rates
            high_error_scenarios = [r for r in load_test_results if r.error_rate > 5.0]
            if high_error_scenarios:
                f.write(f"\nWARNING: High error rates detected at the following load levels:\n")
                for scenario in high_error_scenarios:
                    f.write(f"  - {scenario.concurrent_users} users: {scenario.error_rate:.2f}% error rate\n")
        
        f.write("\n" + "=" * 150 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 150 + "\n")
    
    print(f"\n📊 Comprehensive results exported to {filename}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main entry point for ballot encryption load testing."""
    
    print("\n" + "=" * 100)
    print("BALLOT ENCRYPTION LOAD TESTING FRAMEWORK")
    print("=" * 100)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target API: {BASE_URL}")
    print(f"Test Scenarios: {len(LOAD_SCENARIOS)}")
    print("=" * 100)
    
    # Step 1: Setup guardians (one-time initialization)
    if not setup_guardians():
        print("\n❌ Guardian setup failed. Cannot proceed with load tests.")
        return False
    
    # Step 2: Run all load test scenarios
    print("\n" + "=" * 100)
    print("EXECUTING LOAD TEST SCENARIOS")
    print("=" * 100)
    
    for concurrent_users, requests_per_user in LOAD_SCENARIOS:
        try:
            result = run_load_test_scenario(concurrent_users, requests_per_user)
            load_test_results.append(result)
            
            # Brief pause between scenarios to allow system to stabilize
            time.sleep(2)
            
        except Exception as e:
            print(f"\n❌ Load test scenario failed: {str(e)}")
            import traceback
            traceback.print_exc()
            continue
    
    # Step 3: Generate reports
    print_comprehensive_summary()
    export_results_to_file()
    
    print("\n" + "=" * 100)
    print("🎉 LOAD TESTING COMPLETED SUCCESSFULLY")
    print("=" * 100)
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Scenarios Executed: {len(load_test_results)}")
    print(f"Results saved to: ballot_load_test_results.txt")
    print("=" * 100)
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
