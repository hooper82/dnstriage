import os
from datetime import datetime
from pathlib import Path
from typing import Annotated

import tldextract
from fastapi import FastAPI
from pydantic import BaseModel, Field

MAX_BATCH = 10_000
DNS_NAME = r"^[A-Za-z0-9_-]{1,63}(\.[A-Za-z0-9_-]{1,63})*\.?$"

app = FastAPI(title="dnstriage")
# Bundled public suffix list only: never fetched, never cached to disk.
extract = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None, include_psl_private_domains=True)


def load(path: str) -> set[str]:
    """One name per line, or hosts-file format ("0.0.0.0 bad.example.com"). # starts a comment."""
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    return {word.lower().rstrip(".") for line in lines for word in line.partition("#")[0].split()[-1:]}


BLOCKLIST = load(os.environ.get("BLOCKLIST_PATH", "data/blocklist.txt"))
ALLOWLIST = load(os.environ.get("ALLOWLIST_PATH", "data/allowlist.txt"))


class Record(BaseModel):
    ts: datetime
    client: str
    domain: str = Field(max_length=254, pattern=DNS_NAME)
    qtype: str
    rcode: str


def key(domain: str) -> str:
    """The registrable domain, or the full name if that exact host is blocklisted."""
    name = domain.lower().rstrip(".")
    if name in BLOCKLIST:
        return name
    return extract(name).top_domain_under_public_suffix or name


def verdict(domain: str) -> dict:
    if domain in BLOCKLIST:
        return {"domain": domain, "verdict": "BAD", "source": "blocklist"}
    if domain in ALLOWLIST:
        return {"domain": domain, "verdict": "GOOD", "source": "allowlist"}
    return {"domain": domain, "verdict": "UNKNOWN", "source": "degraded"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ingest")
async def ingest(records: Annotated[list[Record], Field(max_length=MAX_BATCH)]) -> dict:
    keys = dict.fromkeys(key(r.domain) for r in records)
    return {"domains": [verdict(k) for k in keys]}
