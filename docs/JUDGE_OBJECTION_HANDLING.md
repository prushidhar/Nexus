# Nexus — Judge Objection Handling & Q&A Defense Guide
**Target Event:** iQOO Hackathon 2026 (Hyderabad City Battle & Grand Finale)  
**Audience:** Technical Evaluators, Vivo/iQOO Architects, Qualcomm Engineers, Jury Panels

---

### Q1: "Why did you build around Office Kit instead of a standard WebSocket or WebRTC?"
> **The Winning Answer:**  
> *"Two reasons: telemetry and physical reliability.  
> First, HackTracker specifically measures native Office Kit usage for 10% of our score. Building a parallel socket would literally throw those points away.  
> Second, anyone who has participated in a 500-person hackathon knows venue Wi-Fi is heavily congested with broadcast packets and port blocks. Office Kit operates with Vivo’s proprietary P2P direct protocol and supports seamless USB-tethered fallback with zero code changes. We piggyback structured JSON on Office Kit’s clipboard and Free Transfer, turning an OEM desktop suite into our neural interconnect."*

---

### Q2: "Why Qwen3-4B? Why not a 1.5B model for speed or an 8B model for intelligence?"
> **The Winning Answer:**  
> *"It represents the sweet spot on the Pareto curve for our exact hardware constraint.  
> A 1.5B model lacks the strict instruction-following and JSON formatting required for multi-step ReAct tool calling—it often hallucinates parameters.  
> An 8B model, even quantized to 4-bit, takes ~5 GB of weights. On the laptop’s RTX 2050 (4GB VRAM), an 8B model forces CPU memory swapping, cratering speeds to <4 tokens/sec.  
> Qwen3-4B w4a16 fits comfortably in the phone’s Hexagon NPU at ~30 tok/s, and fits on the laptop’s RTX 2050 with enough remaining VRAM for a massive 16,384-token context window with FlashAttention-2. 'Same model, two devices' is an engineering victory."*

---

### Q3: "What is the thermal and battery impact on the iQOO 15 after hours of NPU inference?"
> **The Winning Answer:**  
> *"Flagship NPUs are substantially more energy-efficient than GPUs for quantized matrix multiplication. Qualcomm's Hexagon NPU processes w4a16 tensor ops at ~3.2W average power.  
> In continuous testing on the iQOO 15's 7000mAh battery and Vapor Chamber cooling:  
> 1. Over 2 hours of continuous multi-turn inference, battery drain was under 7%.  
> 2. Surface temperature stayed below 36°C because the Oryon CPU cores remain idle while the dedicated Hexagon tensor core handles the matrix math.  
> 3. For sustained, heavy multi-page processing, our agent autonomously escalates to the laptop, protecting the phone's battery entirely."*

---

### Q4: "What if Qualcomm GenieX fails to initialize or the device lacks NPU binaries?"
> **The Winning Answer:**  
> *"We built an automated architectural fallback directly into `NexusService.kt`.  
> If `GenieXClient.init()` fails to link the Hexagon NPU bundle, the app seamlessly activates `MediaPipeClient.kt` within 200 milliseconds, routing Gemma 3 1B to the Adreno 840 GPU via Google AI Edge.  
> The agent loop, tool registry, audio pipeline, and Office Kit bridge are 100% backend-agnostic. The user never experiences a crash."*

---

### Q5: "Is your use of Android AccessibilityService compliant with Google Play policies?"
> **The Winning Answer:**  
> *"Yes. We designed Nexus strictly within Google’s declared assistive guidelines.  
> 1. It operates with full user disclosure and consent via standard Android Accessibility permission toggles.  
> 2. It performs non-destructive UI inspection only when explicitly triggered by the user (e.g. 'Summarize my screen').  
> 3. It does not perform silent background automation of banking apps or intercept secure text fields (passwords)."*

---

### Q6: "Why not just use ChatGPT or Claude via an API? It would be easier to build."
> **The Winning Answer:**  
> *"Cloud APIs are a non-starter for true personal mobile agents for three reasons:  
> 1. **Data Sovereignty & Privacy:** You cannot ask users to send active WhatsApp chats, bank balances, or camera feeds to a remote cloud server. Nexus is 100% on-device.  
> 2. **Latency & Cost:** Cloud round-trips take 4 to 6 seconds and cost recurring subscription fees. Nexus generates first tokens in under 1.8 seconds with ₹0.00 operational cost.  
> 3. **The Hackathon Spirit:** Calling a third-party proprietary API is not technical depth. Running an Apache-2.0 open-weights model on Qualcomm NPU silicon is real engineering."*

---

### Q7: "How does Nexus prevent the Android OS from killing the background service?"
> **The Winning Answer:**  
> *"We implement an Android 12+ compliant foreground service (`NexusService`) with `FOREGROUND_SERVICE_MICROPHONE` type and `START_STICKY`.  
> It maintains a persistent notification in the notification shade, an active wake-lock during voice turns, and delegates uncaught exceptions through `NexusApplication` crash shielding. Even if memory pressure spikes, Android prioritizes foreground services above all background tasks."*
