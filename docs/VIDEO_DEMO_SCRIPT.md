# Nexus — 2-Minute Video Demo Script & Storyboard
**Target Duration:** Exactly 120 Seconds (2:00)  
**Resolution:** 1080p 60fps (Phone screen record + Camera over-the-shoulder)

---

### [0:00 – 0:20] Hook & Hardware Proof
- **Visual:** Over-the-shoulder shot of the developer holding the iQOO 15 next to the closed ASUS TUF laptop.
- **On-Screen Action:** Swipe down the Android quick settings panel. Tap **Airplane Mode** (Airplane icon turns ON). Wi-Fi and Cellular icons disappear.
- **Voiceover (Confident & Crisp):**
  > *"Meet Nexus — India’s first truly phone-native AI agent built for the iQOO 15. Notice our phone is in Airplane Mode. No Wi-Fi, no cellular, no cloud. Watch what happens when we talk to it."*

---

### [0:20 – 0:45] The Core Offline Voice Loop
- **Visual:** Close-up of the iQOO 15 screen showing the Nexus Cyber Dashboard and floating Overlay HUD.
- **On-Screen Action:** Tap the glowing cyan **Nexus Core** button (or speak).
  - Voice query: *"Hey Nexus, read my screen and tell me what's important."*
- **On-Screen Action:** Nexus floating orb pulses amber with label: `[HEXAGON NPU REASONING]`.
  - In 1.2 seconds, Nexus speaks through the speaker using Piper TTS:
  - Spoken text: *"You are viewing the iQOO 15 hardware dashboard. Hexagon NPU is online running Qwen3-4B w4a16, and battery temperature is optimal at 31 degrees."*
- **Voiceover:**
  > *"Powered by sherpa-onnx streaming Whisper and Qwen3-4B running directly on Qualcomm's Hexagon NPU via GenieX, voice-to-voice reasoning takes under two seconds with zero network latency."*

---

### [0:45 – 1:10] Creative Phone Tools: Vision & Accessibility
- **Visual:** Split-screen — developer holding phone pointing at a paper invoice on the left; phone screen showing live OCR bounding blocks on the right.
- **On-Screen Action:** Tap **Camera OCR**.
  - Camera instantly captures frame.
  - ML Kit Text Recognition groups bounding boxes.
  - Voice query: *"What is the total amount on this receipt?"*
  - Nexus responds aloud: *"The total amount on this invoice is 2,450 rupees, including 18 percent GST."*
- **Voiceover:**
  > *"Because Nexus lives on the device, it has direct sensory access. It inspects screen trees via AccessibilityService and extracts physical text via Camera2 and on-device ML Kit OCR without sending a single pixel to the internet."*

---

### [1:10 – 1:40] The Scored Bridge: Office Kit Escalation
- **Visual:** Wide shot showing the iQOO 15 and the ASUS TUF laptop. The laptop is running Vivo Office Kit Screen Mirroring and the Nexus Watcher daemon.
- **On-Screen Action:** 
  - Voice query on phone: *"Nexus, this research paper is 15 pages long. Escalate to the laptop for deep analysis."*
  - Phone UI shifts state to purple: `[OFFICE KIT ESCALATING]`.
  - Camera pans to laptop terminal: The daemon catches the synced clipboard task instantly!
  - `llama-server` on the laptop's RTX 2050 GPU processes the prompt across a **16,384-token context window** with CUDA acceleration.
  - Laptop writes the result back. Phone clipboard receives it and Nexus speaks the synthesized brief!
- **Voiceover:**
  > *"During the Green Light phase, Nexus doesn't abandon the phone — it coordinates with the laptop. Using iQOO's native Office Kit clipboard sync, Nexus escalates heavy context tasks to the laptop's RTX 2050 GPU, directly boosting our HackTracker telemetry score."*

---

### [1:40 – 2:00] Conclusion & Why Nexus Wins
- **Visual:** Dynamic montage: Floating HUD over a messaging app, live terminal token throughput (~35 tok/s), and team logo.
- **Voiceover:**
  > *"Nexus isn't just a hackathon project — it's the architectural blueprint for the future of mobile AI. 100% offline, 100% private, hardware-accelerated, and natively bridged through Office Kit. Nexus turns phone-first into the ultimate feature. Thank you."*
- **On-Screen End Card:**
  - **NEXUS**
  - iQOO Hackathon 2026 · Hyderabad City Battle
  - Tech Stack: Qualcomm Snapdragon 8 Elite · Hexagon NPU · Qwen3-4B · sherpa-onnx · Vivo Office Kit · RTX 2050
