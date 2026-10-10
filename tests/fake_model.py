"""Fake OpenAI-compatible model: answers every chat completion with a random verdict.

Test tooling, standard library only. Lets the LLM tier run with no real model, no GPU and no
configuration. Its verdicts are meaningless.

Usage: python tests/fake_model.py    (listens on port 8001)
"""
import json
import random
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeModel(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))  # read and ignore the request
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        verdict = {
            "verdict": random.choice(["GOOD", "WARN", "BAD"]),
            "confidence": round(random.random(), 2),
            "reason": "Random verdict from the fake model.",
        }
        body = json.dumps({
            "id": f"fake-{time.time_ns()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "random",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": json.dumps(verdict)},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8001), FakeModel).serve_forever()
