# Nexus — iQOO Hackathon 2026 Pitch & Demo Script
**Track:** Open Innovation · **Duration:** 3 Minutes  
**Target Hardware:** iQOO 15 (Snapdragon 8 Elite) + ASUS TUF (RTX 2050)

---

## 3-Minute Live Demo Choreography

### [0:00 – 0:35] Hook & Offline Proof (Phone-First Execution: 25%)
> *"Judges, every AI assistant today is a thin cloud wrapper — when your network drops or your battery throttles, your agent dies. Nexus is India's first truly phone-native agent.  
> Notice our phone is in **AIRPLANE MODE**. Wi-Fi is OFF, cellular is OFF. Watch this:"*

- **Action:** Tap the Nexus Core button (or say "Hey Nexus")
- **Prompt:** *"What are my active notifications and what time is it?"*
- **Nexus:** Reads notifications instantly via `NexusNotificationService` + responds with on-device TTS.
- **Judge Impact:** Zero network latency, 100% offline proof right on stage.

---

### [0:35 – 1:20] Creative Phone Use (Creative Phone Use: 25%)
> *"Because Nexus lives directly on the iQOO 15's Hexagon NPU, it doesn't just chat — it has direct sensory and mechanical access to your phone's screen and camera."*

- **Action 1 (Screen Intelligence):** Switch to Settings or a long WhatsApp chat.
- **Prompt:** *"Hey Nexus, summarize what's on my screen."*
- **Nexus:** Invokes `read_screen()` via `NexusAccessibilityService`, dumps UI tree, Qwen3-4B synthesizes key points, and speaks back in under 2 seconds.
- **Action 2 (Vision OCR):** Point camera at a paper receipt or badge.
- **Prompt:** *"Hey Nexus, read this receipt and tell me the total amount."*
- **Nexus:** Headless `CameraTool` captures frame, extracts layout via ML Kit OCR, and states the total.

---

### [1:20 – 2:15] The Cross-Device Escalation (Office Kit: 10% + AI-Native: 20%)
> *"Now comes the Green Light power-up. Most teams build custom sockets that fail on crowded venue Wi-Fi and bypass HackTracker. We did something smarter: we made iQOO's official **Office Kit** our compute backbone."*

- **Action:** Office Kit Screen Mirror is already active on the ASUS TUF laptop screen.
- **Prompt:** *"Hey Nexus, this research paper has 15 pages. Escalate to the laptop for deep analysis."*
- **Nexus:** State turns to `OFFICE KIT ESCALATING`. Writes `TaskDescriptor` to clipboard.
- **Laptop:** `watcher.py` catches the synced clipboard, loads Qwen3-4B with a **16,384 context window** on the RTX 2050, runs deep synthesis, and writes the `TaskResult` back to clipboard.
- **Nexus:** Phone detects the result via Office Kit sync, speaks the summary.
- **Judge Impact:** Proves genuine dual-tier cooperation while maxing the HackTracker Office Kit telemetry score.

---

### [2:15 – 3:00] The "Why Not ChatGPT?" Defense & Q&A
> *"Judges will ask: 'Why not just use an API or cloud model?' Here is our 3-point answer:*  
> 1. **Zero Data Leakage:** Your camera frames, screen text, and private messages never leave your phone.  
> 2. **Zero Latency & Cost:** 100% free, runs on the NPU silicon you already paid for.  
> 3. **Hardware-Coordinated:** The exact same open-source Qwen3-4B model runs on the phone's Hexagon NPU during Red Light, and scales to the laptop's RTX 2050 GPU during Green Light through Office Kit.*"

---

## Emergency Fallback Protocols

| What Happened | What To Do |
|---|---|
| Venue Wi-Fi drops Office Kit | Plug in USB cable and use Office Kit USB-Tethered Mirroring (rehearsed pre-event). |
| Voice input fails due to noisy room | Tap the on-screen "📄 Read Screen" or "🎙️ NEXUS CORE" button directly. |
| Judge asks for proof of model | Open the Terminal Log on MainActivity showing `[Qwen3-4B w4a16 @ Hexagon NPU]` with live token rates. |
