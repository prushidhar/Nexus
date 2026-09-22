#!/usr/bin/env python3
"""
Nexus Mock llama-server (Python Built-in Edition)
================================================
Zero-dependency HTTP server simulating llama.cpp on http://127.0.0.1:8080.
Uses only Python standard library (http.server, json, time).
"""

import json
import time
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8080


class MockLLMHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"[{time.strftime('%H:%M:%S')}] {format % args}")

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = json.dumps({"status": "ok", "model": "Qwen3-4B-Instruct-Q4_K_M", "vram_free_mb": 1450})
            self.wfile.write(resp.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/v1/chat/completions":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)

            user_msg = data.get("messages", [{}])[-1].get("content", "")
            print(f"    --> Processing {len(user_msg)} chars via simulated RTX 2050 CUDA...")

            time.sleep(0.35)  # Simulate 350ms inference

            answer = (
                "[NEXUS HIGH-CONTEXT SYNTHESIS — RTX 2050 CUDA]\n\n"
                "Analysis complete across 16,384 token window:\n"
                "1. Snapdragon 8 Elite Hexagon NPU handles voice-to-voice triage offline.\n"
                "2. Laptop RTX 2050 processes extended context without phone thermal load.\n"
                "3. Verified operational through Office Kit sync layer."
            )

            prompt_tokens = len(user_msg.split())
            completion_tokens = len(answer.split())

            response_payload = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "Qwen3-4B-Instruct-Q4_K_M",
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": answer},
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens
                }
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_payload).encode("utf-8"))
            print(f"    <-- Dispatched {completion_tokens} tokens.")
        else:
            self.send_response(404)
            self.end_headers()


def run():
    server = HTTPServer(("127.0.0.1", PORT), MockLLMHandler)
    print("=" * 65)
    print(f"Nexus Mock llama-server listening on http://127.0.0.1:{PORT}/")
    print("Zero-dependency testing ready. Press Ctrl+C to stop.")
    print("=" * 65)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMock server stopped.")


if __name__ == "__main__":
    run()
