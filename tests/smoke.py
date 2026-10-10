"""Smoke test: call the running service and check its responses.

Usage: python tests/smoke.py [base_url]    (default http://localhost:8080)
"""
import json
import sys
import time
import urllib.request

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8080"
failures = 0


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=5) as resp:
        return resp.status, json.load(resp)


def check(name, condition):
    global failures
    print(("PASS " if condition else "FAIL ") + name)
    failures += not condition


# Wait for the service to come up (e.g. straight after `docker compose up`).
for _ in range(20):
    try:
        status, body = get("/health")
        break
    except OSError:
        time.sleep(0.5)
else:
    sys.exit(f"FAIL service not reachable at {BASE}")

check("GET /health returns 200 and status ok", status == 200 and body == {"status": "ok"})

sys.exit(1 if failures else 0)
