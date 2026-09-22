# Nexus — Official Hackathon Submission Portal Copy
**Event:** iQOO Hackathon 2026 · Hyderabad City Battle  
**Track:** Open Innovation ("Local/Open-Source Model at the Core")  
**Project Name:** Nexus  
**Tagline:** The Phone-Native AI Agent that turns on-device silicon into the brain and Office Kit into the bridge.

---

### 1. Project Overview / Elevator Pitch (Under 100 words)
Nexus is India’s first truly phone-native AI agent, engineered from the ground up for the iQOO 15 (Snapdragon 8 Elite) and its native OriginOS Office Kit ecosystem. While conventional AI assistants rely on cloud APIs that leak private data, throttle on poor connectivity, and drain battery, Nexus executes full voice-to-voice reasoning (Whisper $\to$ Qwen3-4B $\to$ Piper) 100% offline on the Hexagon NPU. When sustained computing or deep research is required, Nexus autonomously escalates tasks to an RTX 2050 laptop via Office Kit clipboard sync, scoring directly towards HackTracker metrics.

---

### 2. What Problem Are You Solving? (Under 200 words)
Modern mobile AI assistants are fundamentally "cloud illusions":
1. **Zero Privacy & Data Leakage:** Capturing personal screens, reading notifications, and analyzing paper documents requires sending sensitive telemetry to third-party cloud servers.
2. **Network Fragility:** In real-world Indian conditions—crowded transit, remote regions, or congested venues—cloud assistants stall, stutter, or fail completely.
3. **Wasted Silicon:** Flagship devices like the iQOO 15 boast 70+ TOPS of NPU processing power via the Qualcomm Snapdragon 8 Elite, yet 99% of user applications leave this dedicated AI hardware completely idle.
4. **Device Disconnect:** Users work across both phones and laptops, but existing bridge tools operate as passive file transfer utilities rather than an intelligent, coordinated computing fabric.

Nexus eliminates these problems by making the phone's NPU the primary decision-maker and leveraging iQOO's built-in Office Kit as a smart computational bridge.

---

### 3. The Solution & Key Features (Under 250 words)
Nexus introduces a coordinated two-tier architecture tailored to the hackathon's Red Light / Green Light format:

- **100% Offline Core Loop (Red Light Mode):**
  - **Wake & Speech-to-Text:** sherpa-onnx streaming Whisper tiny.en with voice activity detection (VAD).
  - **On-Device Brain:** Qwen3-4B (w4a16 quantized) executing directly on the Qualcomm Hexagon NPU via GenieX SDK (with MediaPipe Gemma 3 1B GPU fallback).
  - **On-Phone Sensory Tools:** Direct screen reading and automated navigation via `AccessibilityService`; physical document & receipt analysis via Camera2 and on-device ML Kit OCR.
  - **Audio Synthesis:** sherpa-onnx Piper TTS generating natural, conversational spoken replies offline.

- **Cross-Device Escalation (Green Light Mode):**
  - Instead of building fragile third-party sockets, Nexus piggybacks structured JSON tasks (`TaskDescriptor`) directly onto **Office Kit’s shared clipboard and Free Transfer**.
  - A lightweight laptop daemon on the ASUS TUF (RTX 2050 GPU) receives the task, executes extended 16,384-token context analysis using CUDA-accelerated Qwen3-4B, and returns the `TaskResult` back through Office Kit.
  - **Autonomous Web Research:** Executes headless web search and synthesis via the laptop browser agent.

---

### 4. How Did You Build It? (Tech Stack Breakdown)
- **Mobile Hardware Target:** iQOO 15 (Qualcomm Snapdragon 8 Elite Gen 5, Hexagon NPU, Adreno 840 GPU, 16GB LPDDR5X).
- **Mobile Software:** Kotlin, Android SDK 35, Jetpack Coroutines & Serialization, Android AccessibilityService, Camera2 API, ML Kit Text Recognition, WindowManager Floating Overlay.
- **On-Device AI Engines:** Qualcomm GenieX / GENIE Android SDK (Hexagon NPU runtime), Google MediaPipe Tasks GenAI, sherpa-onnx (Whisper + Piper + ONNX Runtime Android).
- **Laptop Hardware & Compute:** ASUS TUF Gaming Laptop (NVIDIA GeForce RTX 2050, 4GB GDDR6 VRAM, CUDA).
- **Laptop Software & Bridge:** `llama.cpp` / `llama-server` (CUDA-accelerated, FlashAttention-2, 16k context), Python 3.11 + `pyperclip` + `watchdog`, and zero-dependency native Windows PowerShell daemon (`watcher.ps1`).
- **Bridge Protocol:** Vivo/iQOO Office Kit native clipboard synchronization and Free Transfer folder automation.

---

### 5. Why Does This Fit the "Phone-First" & "AI-Native" Theme?
Nexus was not ported from a laptop project — it was derived directly from the physical capabilities and scoring rules of the iQOO 15:
1. **Red Light Compliance:** The core voice-agent loop runs with Wi-Fi and Cellular disabled (Airplane Mode). The laptop can be closed, and Nexus retains full functionality.
2. **HackTracker Optimization:** Telemetry scores 15% for raw phone active time and 10% for Office Kit bridge usage. Nexus keeps phone engagement active through its floating overlay service and routes 100% of multi-device tasks through Office Kit.
3. **Creative Hardware Utilization:** Leverages the Hexagon NPU, microphone VAD, Camera2 lens, haptic linear motor, and Accessibility subsystem in a unified ReAct agent loop.

---

### 6. Challenges Faced & How We Overcame Them
1. **NPU Quantization & Framework Novelty:** Integrating Qualcomm's GenieX Android SDK required careful model bundle management. We built an automatic fallback to Google MediaPipe (Gemma 3 1B on Adreno GPU) to guarantee zero downtime.
2. **Strict 4GB VRAM Limit on RTX 2050:** Running large 8B models on a 4GB mobile GPU causes memory thrashing. We standardized on Qwen3-4B across both devices, utilizing the laptop's GPU not for a heavier model, but for an extended 16,384-token context window with FlashAttention-2.
3. **Office Kit Synchronization Latency:** Mitigated by creating an event-driven clipboard watcher with millisecond debouncing and JSON schema validation, ensuring sub-second task hand-off.

---

### 7. Future Roadmap
- **Phase 1 (Post-Hackathon):** Fine-tuning Qwen3-4B with OriginOS-specific tool-calling datasets for deeper app-level automation.
- **Phase 2 (OriginOS Deep Integration):** Publishing an SDK for third-party Android developers to expose custom ReAct tools to Nexus.
- **Phase 3 (Decentralized Local Swarms):** Multi-phone collaborative compute using localized Wi-Fi Direct and Office Kit clusters.
