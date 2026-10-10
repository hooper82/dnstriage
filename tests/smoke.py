"""Smoke test: call the running service and check its responses.

Usage: python tests/smoke.py [--model-down] [base_url]    (default http://localhost:8080)

--model-down: the model endpoint has been stopped; expect degraded verdicts and /ready = degraded.
Run it after a normal run against the same service: it expects that run's cached verdicts.
The concurrency checks assume the default LLM_MAX_CONCURRENCY of 4.
"""
import json
import sys
import threading
import time
import urllib.error
import urllib.request

MODEL_DOWN = "--model-down" in sys.argv
args = [a for a in sys.argv[1:] if a != "--model-down"]
BASE = args[0].rstrip("/") if args else "http://localhost:8080"
failures = 0


def get(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=5) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as err:
        return err.code, json.load(err)


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

# Fresh names each run, so reruns against the same service aren't served from the cache.
run = time.time_ns()
fresh, fresh_gh, invalid = f"smoke{run}.com", f"someone{run}.github.io", f"smoke-invalid-output-{run}.com"
names = ["a.example.com", "B.Example.COM.", "bad.example.com", "x.evil.github.io", fresh_gh, fresh, "localhost",
         invalid]
status, body = post("/ingest", [record(d) for d in names])
entries = {d["domain"]: d for d in body.get("domains", [])}
verdicts = {d: (e["verdict"], e["source"]) for d, e in entries.items()}
check("POST /ingest returns 200", status == 200)
check("ingest groups names by registrable domain, blocklisted hosts separately",
      list(verdicts) == ["example.com", "bad.example.com", "evil.github.io", fresh_gh, fresh, "localhost",
                         invalid])
check("allowlisted domain is GOOD (example.com)", verdicts.get("example.com") == ("GOOD", "allowlist"))
check("blocklisted host under an allowlisted domain is BAD (bad.example.com)",
      verdicts.get("bad.example.com") == ("BAD", "blocklist"))
check("blocklisted registrable domain catches its subdomains (x.evil.github.io)",
      verdicts.get("evil.github.io") == ("BAD", "blocklist"))
check("GET /domains normalises the name and answers from the lists (www.example.com)",
      get("/domains/www.example.com") == (200, {"domain": "example.com", "verdict": "GOOD", "source": "allowlist"}))
check("GET /domains for a never-seen domain is 404", get(f"/domains/never{run}.com")[0] == 404)
if MODEL_DOWN:
    check("with the model down, new unlisted domains are UNKNOWN/degraded",
          all(verdicts.get(d) == ("UNKNOWN", "degraded") for d in [fresh_gh, fresh, invalid]))
    check("a degraded result is cached for a while (GET /domains returns it)",
          get(f"/domains/{fresh}") == (200, {"domain": fresh, "verdict": "UNKNOWN", "source": "degraded"}))
    check("a repeat domain gets the cached UNKNOWN without calling the model",
          post("/ingest", [record(fresh)])[1].get("domains") == [{"domain": fresh, "verdict": "UNKNOWN", "source": "cache"}])
    check("a verdict cached by the earlier normal run is still served (localhost)",
          verdicts.get("localhost", ("", ""))[1] == "cache")
    status, body = post("/ingest", [record(f"down{i}-{run}.com") for i in range(10)])
    check("with the model down, a batch stops calling it after the first wave (1-4 calls for 10 domains)",
          1 <= body.get("model_calls", 0) <= 4 and all(d["source"] == "degraded" for d in body["domains"]))
    check("every domain in that batch is cached as UNKNOWN, skipped ones included",
          all(get(f"/domains/down{i}-{run}.com")[0] == 200 for i in range(10)))
    check("GET /ready reports degraded", get("/ready") == (200, {"status": "degraded"}))
    check("GET /health stays ok while degraded", get("/health") == (200, {"status": "ok"}))
else:
    check("allowlisting github.io doesn't cover other *.github.io sites (goes to the model)",
          verdicts.get(fresh_gh, ("", ""))[1] == "llm")
    model = entries.get(fresh, {})
    check("unlisted domain is classified by the model",
          model.get("source") == "llm" and model.get("verdict") in ("GOOD", "WARN", "BAD"))
    check("model verdict has a confidence 0-1 and a reason of at most 200 characters",
          0 <= model.get("confidence", -1) <= 1 and 0 < len(model.get("reason", "")) <= 200)
    evidence = model.get("evidence", {})
    check("model verdict carries DNS and RDAP evidence (records, or an explicit reason there are none)",
          set(evidence) == {"addresses", "nameservers", "mail", "registered"}
          and all(isinstance(v, list) or v in ("domain does not exist", "no records", "lookup failed")
                  for k, v in evidence.items() if k != "registered")
          and isinstance(evidence["registered"], str))
    check("model output that breaks the schema fails cautious (WARN/llm_invalid)",
          verdicts.get(invalid) == ("WARN", "llm_invalid"))
    check("localhost is classified by the model, or served from an earlier run's cache",
          verdicts.get("localhost", ("", ""))[1] in ("llm", "cache"))
    again = {d["domain"]: d for d in post("/ingest", [record(fresh), record(invalid)])[1]["domains"]}
    check("a repeat domain is served from the cache, with the same verdict",
          again[fresh]["source"] == "cache" and again[fresh]["verdict"] == model.get("verdict"))
    check("invalid model output isn't cached", again[invalid]["source"] == "llm_invalid")
    check("GET /domains returns the cached model verdict with its original source",
          get(f"/domains/{fresh}") == (200, model))
    # Two clients send the same 8 new domains at once; the fake model takes 1 s per smoke-slow call.
    slow = [record(f"smoke-slow-{i}-{run}.com") for i in range(8)]
    replies = []
    threads = [threading.Thread(target=lambda: replies.append(post("/ingest", slow))) for _ in range(2)]
    started = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.monotonic() - started
    check("concurrent requests share in-flight model calls (8 calls for 2 x 8 domains, not 16)",
          sum(r[1].get("model_calls", 0) for r in replies) == 8)
    check("shared calls return model verdicts to both requests",
          all(d["source"] == "llm" for r in replies for d in r[1].get("domains", [])) and len(replies) == 2)
    check(f"model calls run concurrently but capped at 4 (8 x 1 s calls took {elapsed:.1f}s; 2 waves + lookups)",
          1.5 <= elapsed <= 10)  # wide: each call also does real DNS and RDAP lookups
    check("GET /ready reports ok", get("/ready") == (200, {"status": "ok"}))

bad = record("x.com")
del bad["domain"]
check("ingest rejects a record without a domain (422)", post("/ingest", [bad])[0] == 422)
check("ingest rejects a domain that isn't a DNS name (422)", post("/ingest", [record("a b")])[0] == 422)
check("ingest rejects a label over 63 characters (422)", post("/ingest", [record("a" * 64 + ".com")])[0] == 422)
check("ingest accepts a 63-character label", post("/ingest", [record("a" * 63 + ".com")])[0] == 200)
check("ingest rejects a batch over 10,000 records (422)", post("/ingest", [record("x.com")] * 10_001)[0] == 422)

sys.exit(1 if failures else 0)
