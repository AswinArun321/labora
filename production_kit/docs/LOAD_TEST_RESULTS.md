# LABORA — Performance & Load Testing Audit Report

**Document:** `production_kit/docs/LOAD_TEST_RESULTS.md`  
**Date:** 22 November 2026  
**Target:** Realistic Academic Load Testing (up to 1,000 Concurrent Active Users)  
**Budget Objective:** ₹0 Software/Cloud Cost (College On-Premises Hardware)  

---

## 1. Audit Status: `BLOCKED (RUNTIME EXECUTION IN LOCAL AUDIT ENVIRONMENT)`

> [!IMPORTANT]
> **Strict Anti-Fabrication Notice:** In accordance with the audit guidelines (*"Do not fabricate test results. Do not claim support for 1,000 concurrent users unless the actual test has been completed successfully on the intended production-equivalent hardware"*), live progressive load test execution is marked **`BLOCKED`** in this Windows audit environment.
>
> **Reasons for Blocked Status:**
> 1. The Docker Desktop daemon was not running on the Windows host (`failed to connect to docker API at npipe:////./pipe/dockerDesktopLinuxEngine`), preventing local execution of the containerized Gunicorn, PostgreSQL, Redis, and Judge0 CE execution pool.
> 2. The local audit environment is a single developer workstation without the multi-host network infrastructure, dedicated multi-core hardware, or physical CPU resources required to host 1,000 concurrent student sessions and hundreds of simultaneous GCC/Java compilations.

---

## 2. Implemented Load Testing Architecture & Scenario

The complete realistic load testing scenario has been designed and implemented in [production_kit/load_testing/locustfile.py](file:///d:/v/LABORA-Test-Windows/production_kit/load_testing/locustfile.py).

### Workload Characteristics & Cadence:
- **User Population:** Up to 1,000 simulated student sessions (`StudentUser`).
- **Pacing & Think Time:** `wait_time = between(2, 6)` seconds between student interactions, mirroring actual exam behavior.
- **Task Weight Distribution:**
  - `autosave_code` (Weight 10): Monaco editor debounced code saves (simulating typing autosave every ~10–15s).
  - `report_activity_events` (Weight 8): Client telemetry batching (keystrokes, focus changes, clipboard alerts).
  - `open_workspace` (Weight 5): Reading practical instructions, starter code, sample input.
  - `execute_and_poll_code` (Weight 3): Non-blocking asynchronous code dispatch (`POST /run-async/`) followed by polling (`GET /api/executions/<id>/`) every 1.5s until completion.
  - `submit_practical` (Weight 1): Final practical submission upon successful completion.

---

## 3. Staged Capacity Model & Required Acceptance Thresholds

When the college deploys the stack to the target staging server, the load test must be run through the following staged ramp-up:

| Concurrent Users | Ramp Rate | Expected Throughput (RPS) | P95 Latency Target | Queue Depth Target | Target Hardware Sizing |
|---|---|---|---|---|---|
| **50** | 5 users/sec | ~15–25 req/sec | < 250 ms | 0–2 jobs | 4 vCPU / 8 GB RAM (Single Host) |
| **100** | 10 users/sec | ~30–50 req/sec | < 350 ms | 1–5 jobs | 8 vCPU / 16 GB RAM (Single Host) |
| **250** | 25 users/sec | ~75–125 req/sec | < 500 ms | 5–15 jobs | 16 vCPU / 32 GB RAM (Single Host) |
| **500** | 50 users/sec | ~150–250 req/sec | < 800 ms | 15–40 jobs | 24 vCPU / 48 GB RAM (Dual Host Recommended) |
| **750** | 50 users/sec | ~225–375 req/sec | < 1,200 ms | 30–80 jobs | 32 vCPU / 64 GB RAM (Dual Host) |
| **1,000** | 50 users/sec | ~300–500 req/sec | < 1,500 ms | 50–120 jobs | 32+ vCPU / 64+ GB RAM (Dual Host) |

### Strict Pass/Fail SLA Thresholds:
1. **HTTP Error Rate:** Total HTTP 5xx errors must remain **< 0.1%** across the entire test run.
2. **Web API Latency:** 95th percentile latency for autosave, events, and workspace endpoints must remain **< 800ms**.
3. **Execution Polling Resolution:** P95 execution turnaround (time from `POST /run-async/` to state `COMPLETED`) must remain **< 8.0s** under full load.
4. **Database Connection Saturation:** PostgreSQL active connections must not exceed the configured pool ceiling (default 80 connections).
5. **No 504 Worker Exhaustion:** The Django web worker pool must never hang or time out, proving that Celery asynchronous decoupling effectively shields web request threads.

---

## 4. Execution Guide for Target Staging Server

To execute the live progressive load test once the stack is running on the college server:

```bash
# 1. Install Locust on the test driver machine (separate from the server)
pip install locust

# 2. Run progressive 50-user baseline test (5 minutes)
locust -f production_kit/load_testing/locustfile.py \
  --host=https://labora.yourcollege.edu \
  --users 50 --spawn-rate 5 --run-time 5m --headless \
  --csv=load_test_50_users

# 3. Run full 1,000-user stress test (15 minutes)
locust -f production_kit/load_testing/locustfile.py \
  --host=https://labora.yourcollege.edu \
  --users 1000 --spawn-rate 50 --run-time 15m --headless \
  --csv=load_test_1000_users --html=load_test_1000_users.html
```
