"""
Simple load test for the rate limiter. Measures real throughput and
latency against a running local instance of the API gateway.

Usage:
    python3 benchmarks/rate_limit_bench.py
"""
import time
import statistics
import concurrent.futures
import requests

BASE_URL = "http://127.0.0.1:8000"
CONCURRENT_CLIENTS = 20
TOTAL_REQUESTS = 200


def get_token():
    import uuid
    email = f"bench_{uuid.uuid4().hex[:8]}@example.com"
    requests.post(f"{BASE_URL}/api/v1/auth/register", json={"email": email, "password": "benchpass123"})
    resp = requests.post(f"{BASE_URL}/api/v1/auth/login", data={"username": email, "password": "benchpass123"})
    return resp.json()["access_token"]


def make_request(token):
    headers = {"Authorization": f"Bearer {token}"}
    start = time.perf_counter()
    resp = requests.get(f"{BASE_URL}/gateway/ping", headers=headers)
    duration_ms = (time.perf_counter() - start) * 1000
    return resp.status_code, duration_ms


def run_benchmark():
    print(f"Setting up benchmark user...")
    token = get_token()

    print(f"Firing {TOTAL_REQUESTS} requests with {CONCURRENT_CLIENTS} concurrent clients...")
    latencies = []
    status_codes = []

    start_time = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_CLIENTS) as executor:
        futures = [executor.submit(make_request, token) for _ in range(TOTAL_REQUESTS)]
        for future in concurrent.futures.as_completed(futures):
            status, duration = future.result()
            status_codes.append(status)
            latencies.append(duration)
    total_time = time.perf_counter() - start_time

    allowed = status_codes.count(200)
    rejected = status_codes.count(429)
    errors = len(status_codes) - allowed - rejected

    latencies.sort()
    p95_index = int(len(latencies) * 0.95)

    print("\n--- Results (measured, not estimated) ---")
    print(f"Total requests:      {TOTAL_REQUESTS}")
    print(f"Concurrent clients:  {CONCURRENT_CLIENTS}")
    print(f"Total wall time:     {total_time:.2f}s")
    print(f"Requests per second: {TOTAL_REQUESTS / total_time:.2f}")
    print(f"Average latency:     {statistics.mean(latencies):.2f}ms")
    print(f"p95 latency:         {latencies[p95_index]:.2f}ms")
    print(f"Allowed (200):       {allowed}")
    print(f"Rejected (429):      {rejected}")
    print(f"Other/errors:        {errors}")


if __name__ == "__main__":
    run_benchmark()