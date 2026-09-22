#!/usr/bin/env python3
"""
Nexus Laptop LLM Server Supervisor
===================================
Manages local llama.cpp server running Qwen3-4B on NVIDIA GeForce RTX 2050 (4GB VRAM).

Hardware Target:
  - GPU: NVIDIA GeForce RTX 2050 Laptop GPU (Ampere, GA107, 4GB GDDR6)
  - Model: Qwen3-4B-Instruct Q4_K_M GGUF (~2.5 GB weights)
  - VRAM Strategy: 35 GPU layers + FlashAttention-2 + 16,384 context window (~3.6 GB total VRAM used)
  - Port: 8080 (OpenAI-compatible /v1/chat/completions)
"""

import os
import sys
import time
import json
import logging
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [LLM-SERVER] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("NexusLLMServer")

DEFAULT_MODEL_PATH = Path(__file__).parent / "models" / "qwen3-4b-instruct-q4_k_m.gguf"
LLAMA_SERVER_BIN = "llama-server"  # Assumes llama-server is in PATH or current dir
HOST = "127.0.0.1"
PORT = 8080
CTX_SIZE = 16384
GPU_LAYERS = 35


def check_nvidia_gpu():
    """Verify NVIDIA GPU presence and report available VRAM."""
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, check=True
        )
        line = res.stdout.strip().split("\n")[0]
        name, total, free = [x.strip() for x in line.split(",")]
        logger.info(f"Detected GPU: {name} | Total VRAM: {total} MB | Free VRAM: {free} MB")
        return True, int(total)
    except Exception as e:
        logger.warning(f"nvidia-smi check failed or CUDA not found: {e}. Fallback to CPU offload.")
        return False, 0


def is_server_healthy() -> bool:
    """Check if llama.cpp server is responding at /health."""
    url = f"http://{HOST}:{PORT}/health"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NexusSupervisor"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def start_llama_server(model_path: Path):
    """Launch llama.cpp server with optimized flags for RTX 2050 4GB."""
    if not model_path.exists():
        logger.error(f"Model file not found at: {model_path}")
        logger.error("Please download Qwen3-4B Q4_K_M GGUF into laptop/models/ directory.")
        return None

    cmd = [
        LLAMA_SERVER_BIN,
        "-m", str(model_path.resolve()),
        "--host", HOST,
        "--port", str(PORT),
        "--ctx-size", str(CTX_SIZE),
        "--n-gpu-layers", str(GPU_LAYERS),
        "-t", "8",                  # CPU threads
        "--flash-attn",             # FlashAttention-2 reduces KV-cache VRAM
        "--mlock",                  # Lock model in memory
        "--cont-batching",          # Continuous batching for low latency
    ]

    logger.info(f"Starting llama-server: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    return proc


def wait_for_ready(timeout_sec: int = 45) -> bool:
    """Poll health endpoint until llama-server is ready."""
    logger.info(f"Waiting for llama-server to warm up on http://{HOST}:{PORT}...")
    start = time.time()
    while time.time() - start < timeout_sec:
        if is_server_healthy():
            logger.info("llama-server is healthy and ready to process requests!")
            return True
        time.sleep(1.0)
    logger.error("Timed out waiting for llama-server.")
    return False


def query_llm(instruction: str, payload: str, max_tokens: int = 2048) -> dict:
    """OpenAI-compatible inference query with latency and token metrics."""
    url = f"http://{HOST}:{PORT}/v1/chat/completions"
    
    messages = [
        {
            "role": "system",
            "content": (
                "You are Nexus-HighContext, running on the user's laptop (NVIDIA RTX 2050). "
                "You are escalated tasks from the iQOO 15 phone that require deeper analysis, "
                "long context understanding (up to 16,384 tokens), and high precision. "
                "Be thorough, structured, and deliver actionable results."
            )
        },
        {
            "role": "user",
            "content": f"{instruction}\n\n[CONTEXT / DOCUMENT CONTENT]:\n{payload}"
        }
    ]

    data = json.dumps({
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.6,
        "top_p": 0.95
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"}
    )

    t0 = time.time()
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    elapsed = time.time() - t0

    content = result["choices"][0]["message"]["content"]
    usage = result.get("usage", {})
    tokens = usage.get("total_tokens", len(content.split()) * 4 // 3)
    tps = tokens / elapsed if elapsed > 0 else 0

    return {
        "text": content,
        "tokens": tokens,
        "latency_sec": elapsed,
        "tokens_per_sec": tps
    }


if __name__ == "__main__":
    check_nvidia_gpu()
    if not is_server_healthy():
        p = start_llama_server(DEFAULT_MODEL_PATH)
        if p and wait_for_ready():
            try:
                p.wait()
            except KeyboardInterrupt:
                p.terminate()
        else:
            logger.warning("Running in standalone query client mode (connects to existing server).")
    else:
        logger.info("llama-server is already running and ready.")
