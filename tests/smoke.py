"""Smoke test: call the running service and check its responses.

Usage: python tests/smoke.py [base_url]    (default http://localhost:8080)
"""
import json
import sys
import time
import urllib.error
import urllib.request

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8080"
failures = 0


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=5) as resp:
        return resp.status, json.load(resp)


def post(path, payload):
    req = urllib.request.Request(BASE + path, json.dumps(payload).encode(), {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as err:
        return err.code, json.load(err)


def record(domain):
    return {"ts": "2026-10-07T06:00:00Z", "client": "10.0.0.12", "domain": domain, "qtype": "A", "rcode": "NOERROR"}


def check(name, condition):
    global failures
    print(("PASS " if condition else "FAIL ") + name)
    failures += not condition


# Wait for the service to come up (e.g. straight after `docker compose up`).
for _ in range(60):
    try:
        status, body = get("/health")
        break
    except OSError:
        time.sleep(0.5)
else:
    sys.exit(f"FAIL service not reachable at {BASE}")

check("GET /health returns 200 and status ok", status == 200 and body == {"status": "ok"})

names = ["a.example.com", "B.Example.COM.", "bad.example.com", "x.evil.github.io", "someone.github.io", "localhost",
         "smoke-invalid-output.com"]
status, body = post("/ingest", [record(d) for d in names])
entries = {d["domain"]: d for d in body.get("domains", [])}
verdicts = {d: (e["verdict"], e["source"]) for d, e in entries.items()}
check("POST /ingest returns 200", status == 200)
check("ingest groups names by registrable domain, blocklisted hosts separately",
      list(verdicts) == ["example.com", "bad.example.com", "evil.github.io", "someone.github.io", "localhost",
                         "smoke-invalid-output.com"])
check("allowlisted domain is GOOD (example.com)", verdicts.get("example.com") == ("GOOD", "allowlist"))
check("blocklisted host under an allowlisted domain is BAD (bad.example.com)",
      verdicts.get("bad.example.com") == ("BAD", "blocklist"))
check("blocklisted registrable domain catches its subdomains (x.evil.github.io)",
      verdicts.get("evil.github.io") == ("BAD", "blocklist"))
check("allowlisting github.io doesn't cover other *.github.io sites (goes to the model)",
      verdicts.get("someone.github.io", ("", ""))[1] == "llm")
model = entries.get("localhost", {})
check("unlisted domain is classified by the model (localhost)",
      model.get("source") == "llm" and model.get("verdict") in ("GOOD", "WARN", "BAD"))
check("model verdict has a confidence 0-1 and a reason of at most 200 characters",
      0 <= model.get("confidence", -1) <= 1 and 0 < len(model.get("reason", "")) <= 200)
check("model output that breaks the schema fails cautious (WARN/llm_invalid)",
      verdicts.get("smoke-invalid-output.com") == ("WARN", "llm_invalid"))

bad = record("x.com")
del bad["domain"]
check("ingest rejects a record without a domain (422)", post("/ingest", [bad])[0] == 422)
check("ingest rejects a domain that isn't a DNS name (422)", post("/ingest", [record("a b")])[0] == 422)
check("ingest rejects a label over 63 characters (422)", post("/ingest", [record("a" * 64 + ".com")])[0] == 422)
check("ingest accepts a 63-character label", post("/ingest", [record("a" * 63 + ".com")])[0] == 200)
check("ingest rejects a batch over 10,000 records (422)", post("/ingest", [record("x.com")] * 10_001)[0] == 422)

sys.exit(1 if failures else 0)
