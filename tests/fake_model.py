"""Fake Claude: answers every Anthropic Messages API request with a random verdict.

A request mentioning smoke-invalid-output gets a reply that breaks the schema (an over-long reason);
one mentioning smoke-slow is answered after 1 s.

Test tooling, standard library only. Lets the LLM tier run with no real model, no GPU and no
configuration. Its verdicts are meaningless. It ignores request headers and never logs them, so an
ANTHROPIC_API_KEY already exported in your shell goes nowhere.

Usage: python3 tests/fake_model.py    (listens on port 8001; Windows: py)
"""
import json
import random
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeModel(BaseHTTPRequestHandler):
    def do_POST(self):
        request = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path != "/v1/messages":
            self.send_error(404)
            return
        verdict = {
            "verdict": random.choice(["GOOD", "WARN", "BAD"]),
            "confidence": round(random.random(), 2),
            "reason": "Random verdict from the fake model.",
        }
        if b"smoke-invalid-output" in request:  # test trigger: a reason over the 200-character limit
            verdict["reason"] = "x" * 201
        if b"smoke-slow" in request:  # test trigger: a slow model, so concurrent requests overlap
            time.sleep(1)
        body = json.dumps({
            "id": f"msg_fake_{time.time_ns()}",
            "type": "message",
            "role": "assistant",
            "model": "random",
            "content": [{"type": "text", "text": json.dumps(verdict)}],
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8001), FakeModel).serve_forever()
