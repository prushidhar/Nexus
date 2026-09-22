# ⚡ Nexus AI Companion
### *Next-Generation Cross-Device System Intelligence & Local AI Bridge*

[![Platform](https://img.shields.io/badge/Platform-Windows_11_%2B_Android_15-blue.svg)]()
[![Hardware Target](https://img.shields.io/badge/Mobile_SoC-Qualcomm_Snapdragon_8_Elite-00E5FF.svg)](https://qualcomm.com)
[![Laptop Node](https://img.shields.io/badge/Laptop_GPU-NVIDIA_GeForce_RTX_2050_(CUDA)-76B900.svg)]()
[![Core LLM](https://img.shields.io/badge/Local_LLM-Qwen_2.5_GGUF_(llama.cpp)-FFD600.svg)](https://github.com/QwenLM/Qwen2.5)
[![Bridge](https://img.shields.io/badge/Device_Bridge-Vivo%2FiQOO_Office_Kit-7C4DFF.svg)]()
[![Offline Status](https://img.shields.io/badge/Operation-100%25_Offline_Local_First-success.svg)]()

---

## 🌟 Overview

**Nexus AI Companion** is a unified, privacy-first cross-device intelligence system engineered to eliminate the barrier between mobile smartphones and desktop workstations. 

Instead of treating phones and PCs as isolated devices or relying on high-latency cloud APIs, Nexus creates an always-on, bidirectional task pipeline between an **iQOO 15 (Snapdragon 8 Elite)** smartphone and an **ASUS TUF (NVIDIA RTX 2050)** Windows workstation. Powered by local quantized neural models, hardware-accelerated Voice Activity Detection (VAD), and a floating Electron Notch HUD, Nexus enables seamless voice-driven operating system automation, screen-aware dictation, and cross-device task escalation.

---

## ✨ Key Features

- **🎙️ Zero-Latency Voice Pipeline**: Hardware-calibrated Voice Activity Detection (VAD) listening continuously for `"Hey Nexus"` with live ambient noise filtering and zero cloud dependencies.
- **🖥️ Dynamic Notch HUD & Visual Spotlights**: Lightweight, transparent floating Electron overlay accessible via system-wide `Win + Alt` hotkey, complete with animated microphone visualizer and stage badges (*Listening, Reading Screen, Executing*).
- **📱 Vivo Office Kit Cross-Device Bridge**: Bidirectional event synchronization connecting phone sensors and clipboard to desktop processing via local FreeTransfer and Shared Clipboard protocols.
- **🧠 100% On-Device Neural Brain**: Dual-tier inference engine pairing instantaneous deterministic regex fast-paths with local GGUF quantized models (`Qwen 2.5`) running locally via `llama.cpp`.
- **✍️ Screen-Aware Contextual Dictation**: Captures the active foreground window context and injects generated draft responses directly into target input fields.
- **⚙️ Native OS Automation**: Full application launcher (Chrome, VS Code, Spotify, Terminal, Notepad), audio volume controls, and real-time hardware telemetry monitoring.

---

## 🧠 System Architecture

```
+-------------------------------------------------------------------------+
|                  LAPTOP TIER: ASUS TUF (Windows 11)                     |
|                                                                         |
|  +------------------------+  WebSocket  +----------------------------+  |
|  |   Electron Notch HUD   | <---------> |      Nexus Core Daemon     |  |
|  | (Transparent Overlay)  |   (:9876)   |  - Hardware VAD / PyAudio  |  |
|  +------------------------+             |  - SAPI5 High-Speed TTS    |  |
|                                         |  - Local Qwen 2.5 GGUF     |  |
|                                         +--------------+-------------+  |
+--------------------------------------------------------|----------------+
                                                         |
                               Vivo Office Kit Layer     | (Bidirectional)
                   [Shared Clipboard / FreeTransfer Bus] |
                                                         |
+--------------------------------------------------------v----------------+
|                   MOBILE TIER: iQOO 15 (Android 15)                     |
|                                                                         |
|  - Qualcomm Snapdragon 8 Elite Platform                                 |
|  - Sherpa ONNX Streaming Speech Recognition                             |
|  - Android Accessibility Service (UI Hierarchy & Action Injection)      |
|  - Headless Camera2 + OCR Vision Module                                 |
|  - Native Cross-App Floating Control Orb                                |
+-------------------------------------------------------------------------+
```

---

## 📂 Project Structure

```
nexus/
├── android/                         # Android Native Application (Phone Tier)
│   ├── app/src/main/kotlin/com/nexus/agent/
│   │   ├── NexusApplication.kt     # Initialization & safety shields
│   │   ├── NexusService.kt         # Foreground agent lifecycle service
│   │   ├── agent/AgentLoop.kt      # ReAct reasoning loop & tool router
│   │   ├── audio/SherpaASR.kt      # On-device streaming speech recognition
│   │   ├── tools/                  # Camera OCR, Accessibility & Notification tools
│   │   └── ui/MainActivity.kt      # Telemetry & status dashboard
│   └── gradlew.bat                 # Android Gradle build toolchain
│
├── laptop/                          # Desktop Engine & Automation (PC Tier)
│   ├── nexus_daemon.py             # Master background voice daemon & hotkey poller
│   ├── nexus_office_kit.py         # Full bidirectional Vivo Office Kit bridge
│   ├── clicky_bridge.py            # High-performance WebSocket bridge to Notch HUD
│   ├── jarvis_brain.py             # Dual-layer Brain (Fast-Path + Local llama.cpp)
│   ├── jarvis_tools.py             # Windows OS automation (Apps, Volume, Metrics)
│   ├── jarvis_voice.py             # DirectSound PyAudio capture & SAPI5 TTS
│   ├── nexus_dictation.py          # Hands-free contextual typing engine
│   └── nexus_personas.py           # Multi-persona switching module
│
├── bridge/                          # Inter-device event queues & shared memory
│   ├── phone_inbox.json            # Desktop-to-phone commands
│   ├── phone_outbox.json           # Phone-to-desktop events
│   └── shared_clipboard.json       # Live synced clipboard state
│
├── docs/                            # Technical Architecture & Documentation
│   └── ARCHITECTURE.md             # Deep-dive protocol & latency benchmarks
│
├── run_nexus.bat                    # One-click standalone launcher for Windows
└── README.md                        # Project documentation
```

---

## 🚀 Getting Started

### 1. Windows PC Setup
Ensure you have Python 3.10+ installed.

1. **Launch the Nexus Engine**:
   ```cmd
   run_nexus.bat
   ```
2. **Global Hotkey**: Press **`Win + Alt`** anywhere in Windows to expand the Notch HUD.
3. **Voice Command**: Say aloud **`"Hey Nexus, open Chrome"`** or **`"Hey Nexus, what are my routines?"`**.

### 2. Android Phone Setup
1. Open the `android/` directory in **Android Studio**.
2. Connect your **iQOO 15** (or compatible Android 14+ device) with Developer Options enabled.
3. Build and install the APK (`Shift + F10`).
4. Grant the requested Audio, Camera, and Accessibility permissions.

### 3. Pairing the Bridge
1. Connect phone and PC via **Vivo / iQOO Office Kit** with Clipboard Sharing enabled.
2. The PC Notch HUD status badge will turn 🟢 **Connected**, allowing zero-friction handoff between both devices.

---

## 🔒 Privacy & Local-First Philosophy

Nexus was architected around the core principle that personal operating system telemetry, clipboard contents, and screen contexts should never leave the local hardware perimeter. All reasoning, speech processing, and device synchronization execute entirely on the local Snapdragon and GeForce hardware.

---

## 👤 Author

Developed by **P Rushidhar**  
*Project Repository*: [https://github.com/prushidhar/Nexus](https://github.com/prushidhar/Nexus)
