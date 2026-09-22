import os
import sys
import time
import requests

MODEL_URL = "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"
DEST_PATH = r"C:\Users\P RUSHIDHAR\.gemini\antigravity\scratch\nexus-agent\models\qwen2.5-0.5b-instruct-q4_k_m.gguf"

def download_model():
    os.makedirs(os.path.dirname(DEST_PATH), exist_ok=True)
    if os.path.exists(DEST_PATH) and os.path.getsize(DEST_PATH) > 400 * 1024 * 1024:
        print(f"[OK] Model already exists at {DEST_PATH} ({os.path.getsize(DEST_PATH)} bytes)")
        return

    print(f"Downloading Qwen2.5-0.5B GGUF model (~468MB) from {MODEL_URL}...")
    headers = {}
    downloaded = 0
    if os.path.exists(DEST_PATH):
        downloaded = os.path.getsize(DEST_PATH)
        headers['Range'] = f'bytes={downloaded}-'

    response = requests.get(MODEL_URL, headers=headers, stream=True, timeout=30)
    total_size = int(response.headers.get('content-length', 0)) + downloaded
    mode = 'ab' if downloaded > 0 else 'wb'

    start_time = time.time()
    last_print = start_time

    with open(DEST_PATH, mode) as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                now = time.time()
                if now - last_print > 3.0:
                    speed = downloaded / (now - start_time) / (1024 * 1024)
                    pct = (downloaded / total_size * 100) if total_size > 0 else 0
                    print(f"Progress: {downloaded / 1024 / 1024:.1f} MB / {total_size / 1024 / 1024:.1f} MB ({pct:.1f}%) at {speed:.2f} MB/s")
                    last_print = now

    print(f"[SUCCESS] Download completed! Model saved to {DEST_PATH} ({os.path.getsize(DEST_PATH)} bytes)")

if __name__ == '__main__':
    download_model()
