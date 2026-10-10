from fastapi import FastAPI

app = FastAPI(title="dnstriage")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
