# Nexus Pre-Event Setup Checklist (4-Day Sprint)
**Target:** Hyderabad City Battle (26–27 Sep 2026)

---

### Step 1: Qualcomm AI Hub & GenieX SDK
- [ ] Register account at [aihub.qualcomm.com](https://aihub.qualcomm.com)
- [ ] Pull precompiled Qwen3-4B bundle:
  ```bash
  pip install qai-hub
  qai-hub configure --api_key <YOUR_KEY>
  geniex pull ai-hub-models/Qwen3-4B
  ```
- [ ] Place the extracted model files into:
  `android/app/src/main/assets/models/qwen3_4b_w4a16/`

### Step 2: sherpa-onnx Audio Assets
- [ ] Download Whisper tiny.en int8 ONNX files:
  - `encoder.int8.onnx`
  - `decoder.int8.onnx`
  - `tokens.txt`
  Place in: `android/app/src/main/assets/models/sherpa/whisper-tiny.en/`
- [ ] Download Piper voice:
  - `en_US-lessac-low.onnx`
  - `en_US-lessac-low.onnx.json`
  - `espeak-ng-data/`
  Place in: `android/app/src/main/assets/models/sherpa/tts/`

### Step 3: Laptop Setup (ASUS TUF RTX 2050)
- [ ] Install Office Kit from `pc.vivoglobal.com` and pair with iQOO 15
- [ ] Verify Screen Mirroring and Clipboard Synchronization work both ways
- [ ] Download `Qwen3-4B-Instruct-Q4_K_M.gguf` (~2.5 GB) into `laptop/models/`
- [ ] Install dependencies:
  ```powershell
  cd laptop
  pip install -r requirements.txt
  ```
- [ ] Launch `run_laptop_node.bat` and confirm watcher starts cleanly.

### Step 4: Red Light / Green Light Rehearsal
- [ ] Turn phone into **Airplane Mode** — test PTT -> Screen Read -> TTS voice reply.
- [ ] Turn on Office Kit — copy `{"id": "test_01", "instruction": "summarize", "payload": "hello"}` on phone and check if laptop watcher prints task and writes result back.
