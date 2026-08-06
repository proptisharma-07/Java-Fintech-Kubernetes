import asyncio
import json
import random
import time
import uuid

import httpx

TARGET_URL = "http://api.bank.prsou.in/api/auth/register"
TOTAL_REQUESTS = 5000
CONCURRENCY = 10


def build_payload():
    unique_id = uuid.uuid4().hex[:12]
    phone = f"9{random.randint(100000000, 999999999)}"
    return {
        "fullName": f"LoadTest User {unique_id}",
        "email": f"loadtest_{unique_id}@ledgerline.app",
        "phone": phone,
        "password": "password123",
    }


async def fire_request(client: httpx.AsyncClient, sem: asyncio.Semaphore):
    async with sem:
        payload = build_payload()
        start = time.perf_counter()
        try:
            resp = await client.post(TARGET_URL, json=payload, timeout=15.0)
            elapsed_ms = (time.perf_counter() - start) * 1000
            return {"status": resp.status_code, "elapsed_ms": elapsed_ms, "error": None}
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return {"status": 0, "elapsed_ms": elapsed_ms, "error": str(e)}


def percentile(data, pct):
    if not data:
        return 0.0
    idx = int(len(data) * pct)
    idx = min(idx, len(data) - 1)
    return data[idx]


async def run_load_test(total: int, concurrency: int) -> dict:
    sem = asyncio.Semaphore(concurrency)
    start_time = time.perf_counter()

    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(limits=limits) as client:
        tasks = [fire_request(client, sem) for _ in range(total)]
        results = await asyncio.gather(*tasks)

    total_duration = time.perf_counter() - start_time

    response_times = sorted(r["elapsed_ms"] for r in results)
    status_breakdown = {}
    success_count = 0
    failed_count = 0

    for r in results:
        key = str(r["status"]) if r["status"] != 0 else "connection_error"
        status_breakdown[key] = status_breakdown.get(key, 0) + 1
        if r["status"] == 200:
            success_count += 1
        else:
            failed_count += 1

    return {
        "total_requests": total,
        "concurrency": concurrency,
        "success_count": success_count,
        "failed_count": failed_count,
        "status_code_breakdown": status_breakdown,
        "avg_response_time_ms": round(sum(response_times) / len(response_times), 1) if response_times else 0,
        "p95_response_time_ms": round(percentile(response_times, 0.95), 1),
        "p99_response_time_ms": round(percentile(response_times, 0.99), 1),
        "min_response_time_ms": round(min(response_times), 1) if response_times else 0,
        "max_response_time_ms": round(max(response_times), 1) if response_times else 0,
        "total_duration_seconds": round(total_duration, 1),
        "requests_per_second": round(total / total_duration, 1) if total_duration > 0 else 0,
    }


async def main():
    print(f"Target: {TARGET_URL}")
    print(f"Firing {TOTAL_REQUESTS} requests with concurrency {CONCURRENCY}...\n")

    result = await run_load_test(total=TOTAL_REQUESTS, concurrency=CONCURRENCY)

    print("=" * 50)
    print("LOAD TEST RESULTS")
    print("=" * 50)
    print(json.dumps(result, indent=2))
    print("=" * 50)
    print(f"Success: {result['success_count']}/{result['total_requests']}")
    print(f"Failed:  {result['failed_count']}/{result['total_requests']}")
    print(f"Avg response time: {result['avg_response_time_ms']} ms")
    print(f"p95 response time: {result['p95_response_time_ms']} ms")
    print(f"p99 response time: {result['p99_response_time_ms']} ms")
    print(f"Requests/sec: {result['requests_per_second']}")
    print(f"Total duration: {result['total_duration_seconds']} s")


if __name__ == "__main__":
    asyncio.run(main())