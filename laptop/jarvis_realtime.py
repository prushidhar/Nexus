"""
================================================================================
                    JARVIS REAL-TIME MULTIMODAL DESKTOP AGENT
              Powered by openWakeWord + llama.cpp + sherpa-onnx + Vivo Office Kit
================================================================================
"""

import os
import sys
import time
import json
import logging
import threading
from pathlib import Path
from datetime import datetime

# Enable ANSI escape color sequences and UTF-8 output on Windows
os.system("")
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Set up module paths
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
SCRATCH_DIR = PROJECT_ROOT.parent
REPOS_DIR = SCRATCH_DIR / "repos"

sys.path.insert(0, str(CURRENT_DIR))
if (REPOS_DIR / "jarvis" / "src").exists():
    sys.path.insert(0, str(REPOS_DIR / "jarvis" / "src"))

from jarvis_tools import JarvisTools
from jarvis_voice import JarvisTTS, JarvisASR, JarvisWakeDetector
from jarvis_brain import JarvisBrain

logger = logging.getLogger("JarvisRealTime")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


BANNER = """
\033[96m
      _   _    ______     _____  _____ 
     | | / \\  |  _ \\ \\   / /_ _|/ ____|
  _  | |/ _ \\ | |_) \\ \\ / / | | \\___ \\ 
 | |_| / ___ \\|  _ < \\ V /  | |  ___) |
  \\___/_/   \\_\\_| \\_\\ \\_/  |___||____/ 
\033[0m
\033[93m>>> NEXUS / JARVIS REAL-TIME VOICE SYSTEM (100% LOCAL & ZERO-MOCK) <<<\033[0m
================================================================================
* Machine: ASUS TUF Gaming (NVIDIA GeForce RTX 2050 4GB Ampere)
* Phone Link: iQOO 15 (Snapdragon 8 Elite Gen 5 / Hexagon NPU)
* Audio I/O: Logitech G435 Headset + Windows SAPI5 Speech Engine
* Wake Engine: openWakeWord ONNX ('Hey Jarvis')
* Brain Engine: llama.cpp (Qwen2.5-0.5B GGUF) + Fast-Path Intent Routing
* Cross-Device Bridge: Vivo/iQOO Office Kit Clipboard & Task Handoff
================================================================================
"""


class RealTimeJarvis:
    """Master controller for Real-time Jarvis execution loop."""

    def __init__(self):
        self.tts = JarvisTTS(rate=175, volume=1.0)
        self.asr = JarvisASR()
        self.brain = JarvisBrain(use_llm=True)
        self.wake_detector = None
        self._is_busy = False
        self._running = True

    def start(self):
        """Initializes all sensors and starts real-time voice and console loops."""
        print(BANNER)
        
        # 1. Startup Speech aloud
        startup_phrase = (
            "Jarvis online. All subsystems operational. "
            "Neural cognitive matrix engaged. Standing by for your command, Sir."
        )
        self.tts.speak(startup_phrase)

        # 2. Start Vivo Office Kit Background Watcher
        bridge_thread = threading.Thread(target=self._office_kit_watcher_loop, daemon=True)
        bridge_thread.start()

        # 3. Start Wake Word Detector in background
        try:
            self.wake_detector = JarvisWakeDetector(threshold=0.28, on_wake=self._on_wake_triggered)
            self.wake_detector.start()
        except Exception as e:
            logger.warning(f"Could not start openWakeWord background loop: {e}")

        # 4. Interactive Console & Voice Command Loop
        self._interactive_console_loop()

    def _on_wake_triggered(self):
        """Callback invoked when 'Hey Jarvis' wake word is detected."""
        if self._is_busy:
            return
        
        self._is_busy = True
        if self.wake_detector:
            self.wake_detector.pause()

        try:
            print("\n\033[92m[>>> WAKE EVENT TRIGGERED <<<]\033[0m")
            self.tts.speak("At your service, Sir.")
            
            # Short cooldown so TTS audio finishes reverberating in the room
            time.sleep(0.2)

            # Listen for command with exclusive mic access
            query = self.asr.listen(timeout=6.0, phrase_limit=10.0)
            if query:
                self._handle_user_query(query)
            else:
                print("\033[90m[Jarvis: No command heard - standing by for 'Hey Jarvis']\033[0m")
        finally:
            time.sleep(0.4)
            if self.wake_detector:
                self.wake_detector.resume()
            self._is_busy = False

    def _handle_user_query(self, query: str):
        """Processes user voice or text query, speaks reply, and executes tool."""
        print(f"\n\033[94m[PROCESSING QUERY]\033[0m: {query}")
        speech_reply, tool_res = self.brain.process_query(query)

        # Speak answer aloud
        self.tts.speak(speech_reply)

        # Print tool outcome
        if tool_res:
            print(f"\033[92m[TOOL EXECUTED]\033[0m: {json.dumps(tool_res, indent=2)}")

    def _interactive_console_loop(self):
        """
        Console command listener:
        - Press [ENTER] with empty text: triggers microphone voice capture immediately!
        - Type any command (e.g. 'open chrome', 'status', 'screenshot'): executes directly!
        - Type 'exit' or 'quit': terminates system cleanly.
        """
        print("\n\033[1;33m[JARVIS READY]\033[0m Options:")
        print("  - Say aloud: \033[1;32m'Hey Jarvis'\033[0m (via G435 Headset)")
        print("  - Press \033[1;36m[ENTER]\033[0m on blank line to speak immediately (Push-To-Talk)")
        print("  - Or type any command directly below and press [ENTER]\n")

        while self._running:
            try:
                user_input = input("\033[93mJARVIS >> \033[0m").strip()
                
                if user_input.lower() in ["exit", "quit", "shutdown"]:
                    self.tts.speak("Shutting down Jarvis systems. Goodbye, Sir.")
                    self._running = False
                    break

                if not user_input:
                    # Push-to-Talk triggered by Enter key
                    print("\033[96m[Push-To-Talk Activated]\033[0m")
                    self._is_busy = True
                    if self.wake_detector:
                        self.wake_detector.pause()
                    try:
                        spoken_query = self.asr.listen(timeout=6.0, phrase_limit=10.0)
                        if spoken_query:
                            self._handle_user_query(spoken_query)
                        else:
                            print("[ASR] No speech detected.")
                    finally:
                        time.sleep(0.3)
                        if self.wake_detector:
                            self.wake_detector.resume()
                        self._is_busy = False
                else:
                    # Typed command
                    self._is_busy = True
                    if self.wake_detector:
                        self.wake_detector.pause()
                    try:
                        self._handle_user_query(user_input)
                    finally:
                        time.sleep(0.3)
                        if self.wake_detector:
                            self.wake_detector.resume()
                        self._is_busy = False

            except (KeyboardInterrupt, EOFError):
                print("\n[!] Session ended.")
                self._running = False
                break
            except Exception as e:
                logger.error(f"Console loop error: {e}")

        if self.wake_detector:
            self.wake_detector.stop()

    def _office_kit_watcher_loop(self):
        """Continuously monitors incoming events from the iQOO 15 phone."""
        bridge_file = PROJECT_ROOT / "bridge" / "phone_outbox.json"
        last_processed_id = None

        while self._running:
            try:
                if bridge_file.exists():
                    with open(bridge_file, "r", encoding="utf-8") as f:
                        events = json.load(f)
                    
                    if events and isinstance(events, list):
                        latest = events[-1]
                        event_id = latest.get("id")
                        if event_id and event_id != last_processed_id:
                            last_processed_id = event_id
                            action = latest.get("action", "UNKNOWN")
                            payload = latest.get("payload", {})
                            print(f"\n\033[95m[OFFICE KIT EVENT FROM iQOO 15]\033[0m: Action={action}")
                            
                            if action == "HANDOFF_REQUEST":
                                text = payload.get("text", "New request from phone")
                                self.tts.speak(f"Sir, incoming handoff from your iQOO 15: {text}")
                                self._handle_user_query(text)
                            elif action == "PHONE_BATTERY_LOW":
                                self.tts.speak("Warning, Sir. Your iQOO 15 battery has dropped below 15 percent.")

                time.sleep(2.0)
            except Exception as e:
                time.sleep(3.0)


if __name__ == "__main__":
    jarvis = RealTimeJarvis()
    jarvis.start()
