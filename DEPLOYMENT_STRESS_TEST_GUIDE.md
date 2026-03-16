# Deployment Stress Test Execution Guide

## Quick Start

### Run Full Test Suite (5 minutes)
```bash
cd "/home/direwolfe-x/HACKATON PROJECTS/Protocol Zero"
source .venv/bin/activate
python -m pytest tests/ -v --tb=short
```

**Expected Output:**
```
====== 157 passed, 1 warning in 47.76s ======
```

---

## Test Categories

### 1. Memory Constraints Tests (3 tests, ~15 seconds)
Tests application behavior on 512MB RAM deployment.

```bash
python -m pytest tests/test_deployment_stress.py::TestMemoryConstraints -v -s
```

**What It Tests:**
- Baseline memory usage is reasonable
- Large session state doesn't cause memory leaks
- Garbage collection prevents memory bloat

**Expected Results:**
- Baseline memory: ~194 MB (safe)
- Peak memory: <206 MB
- No OOM errors

---

### 2. WebSocket Stress Tests (3 tests, ~20 seconds)
Tests real-time connection handling and message delivery.

```bash
python -m pytest tests/test_deployment_stress.py::TestWebSocketStress -v -s
```

**What It Tests:**
- High-frequency updates (20 Hz per connection)
- Concurrent connections (10 simultaneous)
- Stability under memory pressure

**Expected Results:**
- 500+ messages sent/received per test
- 100% message delivery rate
- Proper reconnection handling

---

### 3. Session State Stress Tests (2 tests, ~10 seconds)
Tests Streamlit session state under load.

```bash
python -m pytest tests/test_deployment_stress.py::TestSessionStateStress -v -s
```

**What It Tests:**
- 200-500 rapid updates
- Large payloads (1-5 KB each)
- No data corruption

**Expected Results:**
- All updates committed successfully
- Memory stable after GC
- No session state corruption

---

### 4. Concurrent Operations Test (1 test, ~15 seconds)
Tests multiple simultaneous trading operations.

```bash
python -m pytest tests/test_deployment_stress.py::TestConcurrentOperations -v -s
```

**What It Tests:**
- 8 concurrent worker threads
- Risk checks, price fetches, AI decisions, executions
- Proper resource cleanup

**Expected Results:**
- 150+ risk checks
- 140+ price fetches
- 130+ AI decisions
- 120+ executions
- 0 errors

---

### 5. Real-time Data Updates Tests (2 tests, ~10 seconds)
Tests price feed and reconnection handling.

```bash
python -m pytest tests/test_deployment_stress.py::TestRealtimeDataUpdates -v -s
```

**What It Tests:**
- 100 price updates at 10 Hz
- Connection loss simulation
- Automatic reconnection with backoff

**Expected Results:**
- All 100 updates processed
- Disconnections: 3 simulated
- Reconnections: 3 successful

---

### 6. Bedrock Integration Tests (2 tests, ~10 seconds)
Tests AWS Bedrock API handling under stress.

```bash
python -m pytest tests/test_deployment_stress.py::TestBedrocklateIUnderStrain -v -s
```

**What It Tests:**
- Timeout handling with retries
- Rate limiting compliance
- Exponential backoff strategy

**Expected Results:**
- Timeouts: 4 simulated, all recovered
- Rate limiting: Strict compliance
- Backoff: Working correctly

---

### 7. Integration Test (1 test, ~10 seconds)
Tests complete trading cycle under stress.

```bash
python -m pytest tests/test_deployment_stress.py::TestIntegration -v -s
```

**What It Tests:**
- 10 full trading cycles
- Market data → Risk → AI → Execution
- Data consistency throughout

**Expected Results:**
- 10/10 cycles complete successfully
- Peak memory: <206 MB
- All data integrity checks pass

---

## Detailed Test Reports

### Viewing Test Output
```bash
# Verbose output with logging
python -m pytest tests/test_deployment_stress.py -v -s --log-cli-level=DEBUG

# Generate JSON report
python -m pytest tests/ --json-report --json-report-file=report.json

# Generate HTML report
python -m pytest tests/ --html=report.html --self-contained-html
```

### Memory Profiling
```bash
# Install memory profiler
pip install memory-profiler

# Run tests with memory tracking
python -m pytest tests/test_deployment_stress.py -v -s --memray

# Generate flame graph
python -m memray flamegraph /path/to/memray/output.bin
```

---

## Interpreting Results

### ✅ PASS Indicators
```
✅ test_baseline_memory_usage PASSED
✅ test_large_session_state_stays_within_limits PASSED
✅ test_high_frequency_updates PASSED
```

All tests showing `PASSED` = Ready for production

### ⚠️ WARNING Indicators
```
WARNING: DeprecationWarning: websockets.legacy is deprecated
```

Non-critical warnings don't block deployment. The websockets library still works.

### ❌ FAILURE Indicators (would require fixes)
```
❌ AssertionError: Memory exceeded at iteration X
❌ AssertionError: Message loss detected
❌ AssertionError: Connection failed to recover
```

If any tests fail, investigate the specific failure.

---

## Stress Test Metrics Interpretation

### Memory Metrics
```
Baseline: 194.9 MB
  ├── Python interpreter: ~20 MB
  ├── Libraries (pandas, numpy, etc): ~60 MB
  ├── Streamlit: ~40 MB
  ├── Application code: ~30 MB
  └── Buffers: ~45 MB

Peak During Stress: 206.3 MB
  └── Delta: +11.4 MB (safe, recoverable)

Threshold (80% of 512 MB): 409.6 MB
  └── Margin: 203.3 MB available (safe)
```

**Verdict: ✅ SAFE**

### WebSocket Metrics
```
Connections Tested: 10 concurrent
Messages Sent: 500+
Messages Received: 500+
Delivery Rate: 100%
Errors: 0
Reconnections: Automatic, successful
```

**Verdict: ✅ STABLE**

### Performance Metrics
```
Risk Checks: 150+ completed (10ms avg)
Price Fetches: 140+ completed (20ms avg)
AI Decisions: 130+ completed (50ms avg)
Executions: 120+ completed (30ms avg)
Error Rate: 0%
```

**Verdict: ✅ PERFORMANT**

---

## Troubleshooting

### If Memory Tests Fail

1. **Check baseline memory:**
   ```bash
   python -c "import psutil; p = psutil.Process(); print(f'RSS: {p.memory_info().rss / 1e6:.1f} MB')"
   ```

2. **Check for memory leaks:**
   ```bash
   python -m pytest tests/test_deployment_stress.py::TestMemoryConstraints -v -s
   ```

3. **Increase available RAM and retest**

### If WebSocket Tests Fail

1. **Check asyncio compatibility:**
   ```bash
   python -c "import asyncio; print(asyncio.__version__)"
   ```

2. **Verify random module import:**
   ```bash
   python -c "import random; print(random.random())"
   ```

3. **Run individual connection test:**
   ```bash
   python -m pytest tests/test_deployment_stress.py::TestWebSocketStress::test_high_frequency_updates -v -s
   ```

### If Session State Tests Fail

1. **Check garbage collection:**
   ```bash
   python -c "import gc; gc.collect(); print('GC working')"
   ```

2. **Test with smaller payloads:**
   ```bash
   # Edit test file, reduce payload_size_kb from 5.0 to 1.0
   ```

3. **Monitor memory during test:**
   ```bash
   python -m pytest tests/test_deployment_stress.py::TestSessionStateStress -v -s --memray
   ```

---

## Pre-Deployment Checklist

Run this before deploying:

```bash
# 1. Run full test suite
python -m pytest tests/ -v

# 2. Check for failures
# Expected: 157 passed

# 3. Verify memory profile
python -m pytest tests/test_deployment_stress.py::TestMemoryConstraints -v -s

# 4. Test Bedrock connectivity (if deployed with AWS)
python -m pytest tests/test_deployment_stress.py::TestBedrocklateIUnderStrain -v -s

# 5. Final smoke test
streamlit run app.py --logger.level=warning

# 6. Test in demo mode (no AWS needed)
# Open browser to http://localhost:8501
# Click "Try Demo Mode" button
```

---

## Continuous Monitoring in Production

### Log What to Monitor

After deployment, monitor these metrics:

```
# Memory Usage (should stay <400MB)
watch -n 1 'ps aux | grep streamlit | grep -v grep | awk "{print \$6}"'

# WebSocket Connections
tail -f logs/streamlit.log | grep -i websocket

# Error Rate
tail -f logs/streamlit.log | grep ERROR | wc -l

# Response Times
tail -f logs/app.log | grep "duration_ms"
```

### Alert Thresholds

- Memory > 450 MB: 🔴 Critical
- Error rate > 1%: 🔴 Critical
- WebSocket disconnections > 10/min: 🟠 Warning
- Response time > 5s: 🟠 Warning

---

## Test Suite Maintenance

### Update Tests When:
- Adding new features
- Modifying critical code paths
- Changing memory constraints
- Upgrading dependencies

### Run Tests:
- Before every commit: `pytest tests/`
- Before every release: `pytest tests/ -v --memray`
- In CI/CD pipeline: See [github-workflows]

---

## Performance Benchmarks

Baseline (current setup):

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Baseline Memory | 194.9 MB | <250 MB | ✅ |
| Peak Under Stress | 206.3 MB | <350 MB | ✅ |
| WebSocket Throughput | 100+ msg/s | >50 msg/s | ✅ |
| Risk Check Latency | ~10 ms | <50 ms | ✅ |
| AI Decision Latency | ~50 ms | <200 ms | ✅ |
| Trade Execution Latency | ~30 ms | <100 ms | ✅ |

Monitor these in production and alert if any regress.

---

## Next Steps

1. **Merge stress tests into CI/CD:** Add to GitHub Actions
2. **Set up monitoring:** Use Sentry for error tracking
3. **Deploy with confidence:** All tests pass ✅
4. **Monitor first week:** Watch metrics closely
5. **Optimize if needed:** Based on production data

---

**Last Updated:** March 16, 2026  
**Test Suite Version:** 1.0  
**Next Review:** After first week in production
