# dnstriage

A small inference service that classifies DNS domains as GOOD, WARN, BAD or UNKNOWN, using curated lists first and falling back to an LLM for unknown domains.

> **Status: work in progress.**
> A sample run will appear here as features land.

## Quick start

Needs Python 3.12+ (or just Docker). The service listens on http://localhost:8080.

**Linux / macOS**

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
python3 tests/fake_model.py &       # stand-in model on port 8001 (or run it in a second terminal)
.venv/bin/python -m uvicorn app.main:app --port 8080
```

**Windows (PowerShell)**

```powershell
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
Start-Process py tests/fake_model.py   # stand-in model on port 8001, in its own window
.venv\Scripts\python -m uvicorn app.main:app --port 8080
```

**Docker**

```bash
docker compose up --build    # starts the service and the fake model
```

Unknown domains are classified by a model. Until you point it at a real one, a **fake model**
(`tests/fake_model.py`) answers with random verdicts, so everything runs with no configuration.

**Check it works.** In a second terminal, run the smoke test (standard library only, so any Python 3 will do):

```bash
python tests/smoke.py
```

To see degraded mode, stop the fake model and run `python tests/smoke.py --model-down`: new unknown
domains come back `UNKNOWN`/`degraded` (and stay `UNKNOWN` for 10 minutes, so a down model is left alone), domains the model already classified
are still served from the cache, the lists keep working, and `/ready` reports `degraded`.

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness. |
| `GET` | `/domains/{domain}` | A domain's verdict: from the lists, else the cached model verdict, else 404. |
| `GET` | `/metrics` | Prometheus metrics: `dnstriage_decisions_total` by `source` (redirects to `/metrics/`). |
| `GET` | `/ready` | Model status: `ok`, or `degraded` if the last model call failed. Always HTTP 200. |
| `POST` | `/ingest` | Classify a batch (JSON array, up to 10,000) of DNS query records; returns one verdict per registrable domain, and `model_calls`. |

A record looks like this:

```json
{ "ts": "2026-10-07T06:00:00Z", "client": "10.0.0.12", "domain": "example.com", "qtype": "A", "rcode": "NOERROR" }
```

Interactive docs are at http://localhost:8080/docs.

## Configuration

All settings are optional environment variables; the defaults run the demo as-is.

| Variable | Default | Purpose |
|---|---|---|
| `BLOCKLIST_PATH` | `data/blocklist.txt` | Known-bad domains (`BAD`). One per line or hosts-file format, e.g. the abuse.ch URLhaus hostfile. |
| `ALLOWLIST_PATH` | `data/allowlist.txt` | Known-good registrable domains (`GOOD`), e.g. the Tranco top 100k. |
| `OPENAI_BASE_URL` | `http://localhost:8001/v1` | OpenAI-compatible model endpoint. The default is the fake model. |
| `OPENAI_API_KEY` | `not-needed` | Key for the endpoint, if it needs one. |
| `MODEL_NAME` | `random` | Model to use (the fake model ignores it). |
| `CACHE_TTL_S` | `86400` | Seconds to keep a model verdict before asking the model again. |
| `LLM_MAX_CONCURRENCY` | `4` | Model calls allowed in flight at once. |
| `LLM_TIMEOUT_S` | `20` | Seconds to wait for the model before marking a domain `degraded`. |

The bundled lists are tiny samples with fake or reserved names. Lists are read at startup.

## Documents

- [DESIGN.md](DESIGN.md): purpose, architecture, decisions and threat model.
- [CLAUDE.md](CLAUDE.md) and [.claude/](.claude): how this project is built with Claude Code.

## Scope

This is a proof of concept. DNS logs are pushed to this service, while reports are pulled.

## Outside of Scope
* Event Collection - DNS logs need to be transformed and pushed to this service. Log collection, encrypted DNS (DoH/DoT) or VPNs are all outside of this service and would need to be dealt with upstream.
* Retention - Currently uses an in-memory data store, so state is lost on restart. This would need to move to a permanent DB such as SQLite or Postgres.
* Alerting - Service doesn't have a threshold for how many bad-domains or any severity level for a query.
* Context - There are good reasons for accessing BAD domains - this service only tracks, it makes no judgement as to if a node is compromised or not.
* Live reputation - The blocklist and allowlist are static files, so they go out of date. A future version would ask a domain reputation API about each domain the local lists don't cover, keeping the local lists as overrides. Suitable APIs all need a key or sign-up, so this is left out to keep the service runnable with no configuration.
* External lookups - Each unknown domain (never client IPs or full names) is looked up in DNS and in RDAP (rdap.org). That traffic leaves your network and can reach the domain owner's own nameservers. Failed lookups are passed to the model as "lookup failed", without retries.
* Security - No authentication, authorisation or TLS. Any client that can reach the service can push logs and read reports. Run it on a trusted network, or put it behind a reverse proxy that handles TLS and authentication.
