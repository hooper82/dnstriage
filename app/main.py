from datetime import datetime
from typing import Annotated

import tldextract
from fastapi import FastAPI
from pydantic import BaseModel, Field

MAX_BATCH = 10_000
DNS_NAME = r"^[A-Za-z0-9_-]{1,63}(\.[A-Za-z0-9_-]{1,63})*\.?$"

app = FastAPI(title="dnstriage")
# Bundled public suffix list only: never fetched, never cached to disk.
extract = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None, include_psl_private_domains=True)


class Record(BaseModel):
    ts: datetime
    client: str
    domain: str = Field(max_length=254, pattern=DNS_NAME)
    qtype: str
    rcode: str


def registrable(domain: str) -> str:
    name = domain.lower().rstrip(".")
    return extract(name).top_domain_under_public_suffix or name


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ingest")
async def ingest(records: Annotated[list[Record], Field(max_length=MAX_BATCH)]) -> dict:
    domains = dict.fromkeys(registrable(r.domain) for r in records)
    return {"domains": [{"domain": d, "verdict": "UNKNOWN", "source": "degraded"} for d in domains]}
