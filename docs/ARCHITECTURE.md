# Nexus — System Architecture & Technical Whitepaper
**Document Version:** 1.0.0-PROD · **Target Hardware:** Snapdragon 8 Elite + RTX 2050  
**Authors:** Team Nexus · iQOO Hackathon 2026

---

## 1. High-Level Architecture

Nexus establishes a dual-tier agent architecture mapped to the hackathon's **Red Light / Green Light** operational phases:

```
+=================================================================================+
|                      TIER A: PHONE-NATIVE COMPUTE (RED LIGHT)                    |
|                            Device: iQOO 15 (OriginOS 6)                         |
+=================================================================================+
|  [Input Stage]                                                                  |
|    Microphone PCM Stream (16kHz) -> sherpa-onnx OnlineRecognizer (Whisper tiny) |
|    Dynamic Energy VAD (Amplitude Windowing, Silence Timeout = 1500ms)           |
+---------------------------------------------------------------------------------+
|  [Reasoning & Planning Stage]                                                   |
|    AgentLoop: ChatML Prompt -> Qwen3-4B w4a16 @ Qualcomm Hexagon NPU (GenieX)   |
|    Fallback Subsystem: Gemma 3 1B int4 @ Adreno 840 GPU (Google MediaPipe)      |
|    Max ReAct Iterations = 5 | Sliding Context Window = 6 Turns                  |
+---------------------------------------------------------------------------------+
|  [Sensory & Mechanical Tool Stage]                                              |
|    - NexusAccessibilityService: Traverses active AccessibilityNodeInfo tree     |
|    - CameraTool: Headless Camera2 HAL3 capture -> Google ML Kit OCR             |
|    - NexusNotificationService: Intercepts and parses status notifications       |
|    - OfficeKitBridge: Dispatches JSON payload to system clipboard               |
+---------------------------------------------------------------------------------+
|  [Output Stage]                                                                 |
|    Synthesized Response -> sherpa-onnx OfflineTts (Piper ONNX)                  |
|    AudioTrack Static Buffer Stream -> High-Fidelity Assistant Channel           |
+=================================================================================+
                                        |
                 [Office Kit IPC Synchronization Backbone]
                 Piggybacked on ClipboardManager & Free Transfer
                                        |
+=================================================================================+
|                    TIER B: LAPTOP-AUGMENTED COMPUTE (GREEN LIGHT)               |
|                      Device: ASUS TUF Gaming (NVIDIA RTX 2050)                  |
+=================================================================================+
|  [Watcher Daemon]                                                               |
|    watcher.py / watcher.ps1: Event polling (250ms interval) on clipboard/files  |
|    Schema Validator: Verifies TaskDescriptor JSON UUID, timestamp & payload     |
+---------------------------------------------------------------------------------+
|  [Extended Context Inference]                                                   |
|    llama-server: Qwen3-4B Q4_K_M GGUF                                           |
|    Parameters: --n-gpu-layers 35 --ctx-size 16384 --flash-attn                  |
|    VRAM Allocation: 2.5 GB Weights + 1.1 GB KV-Cache <= 4.0 GB GDDR6 Budget     |
+---------------------------------------------------------------------------------+
|  [Autonomous Web Intelligence]                                                  |
|    browser_agent.py: Headless research crawler & multi-snippet synthesizer      |
+=================================================================================+
```

---

## 2. Memory & Compute Budget

### 2.1 Mobile Tier (iQOO 15 — 16GB LPDDR5X)
| Component | Runtime / Execution Unit | Memory Footprint | Latency Target |
|---|---|---|---|
| OS & OriginOS 6 Base | System Kernels & Daemons | ~4.5 GB | Baseline |
| Qwen3-4B w4a16 | Hexagon NPU (HTP V79) | ~2.4 GB | ~28–35 tok/s |
| sherpa-onnx ASR | CPU (Kryo Oryon cores) | ~180 MB | Real-time (0.2x RTF) |
| sherpa-onnx Piper TTS | CPU (Kryo Oryon cores) | ~95 MB | < 250ms synthesis |
| ML Kit OCR | Hexagon DSP / GPU | ~65 MB | < 300ms / frame |
| App Runtime & HUD | JVM / Android Runtime | ~110 MB | 60 FPS render |
| **Total Footprint** | | **~7.35 GB / 16 GB** | **Zero thermal throttling** |

### 2.2 Laptop Tier (ASUS TUF — 4GB GDDR6 RTX 2050)
The NVIDIA RTX 2050 mobile GPU features 2048 CUDA cores on a 64-bit memory bus with a strict 4096 MB VRAM ceiling. Attempting to run an 8B model requires CPU offloading, dropping generation speeds to an unusable 2–4 tok/s.
- **Solution:** Run Qwen3-4B Q4_K_M (~2.5 GB weights).
- **GPU Layer Offload:** 35 layers offloaded to CUDA (`--n-gpu-layers 35`).
- **Context Allocation:** 16,384 tokens with FlashAttention-2 consumes ~1.1 GB VRAM.
- **Total VRAM Consumption:** ~3.6 GB / 4.0 GB, leaving 400 MB headroom for Windows DWM and display composition.

---

## 3. Communication Protocol (Office Kit IPC)

### 3.1 Task Hand-Off Payload (`TaskDescriptor.kt`)
```json
{
  "id": "a9f4c82b",
  "type": "LONG_CONTEXT_ANALYSIS",
  "payload": "Raw extracted document text or research question...",
  "instruction": "Summarize key architectural trade-offs in 3 bullet points",
  "returnChannel": "clipboard",
  "createdAt": "2026-09-22T06:42:28.236Z"
}
```

### 3.2 Task Result Payload (`TaskResult.kt`)
```json
{
  "taskId": "a9f4c82b",
  "result": "1. Local NPU execution guarantees privacy and zero latency.\n2. Cross-device coordination extends context window to 16k tokens without phone thermal pressure.\n3. Office Kit piggybacking maximizes HackTracker scoring automatically.",
  "tokenCount": 184,
  "source": "laptop_qwen3_4b_cuda_rtx2050",
  "completedAt": "2026-09-22T06:42:30.114Z"
}
```

---

## 4. Fallback & Fault-Tolerance Matrix

| Failure Mode | Detection Mechanism | Automated Mitigation |
|---|---|---|
| **GenieX NPU SDK Classloader Miss** | `ClassNotFoundException` during `init()` | `MediaPipeClient` automatically instantiates Gemma 3 1B on Adreno 840 GPU. |
| **Microphone Background Killing** | OS Low-Memory Killer (LMK) | `NexusService` is declared as `FOREGROUND_SERVICE_MICROPHONE` with `START_STICKY`. |
| **Venue Wi-Fi Congestion** | Office Kit clipboard sync latency > 30s | USB-tethered Office Kit pairing active; fallback to on-device reasoning if timeout expires. |
| **Python Missing on Laptop** | `run_laptop_node.bat` environment probe | Auto-falls back to zero-dependency native Windows PowerShell daemon (`watcher.ps1`). |
| **AAPT2 Icon Resource Missing** | Build validation check | Adaptive vector XML drawables compiled directly into Android package. |
