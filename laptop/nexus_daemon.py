"""
NEXUS BACKGROUND VOICE DAEMON & CLICKY COMPANION INTEGRATION
Runs 100% invisibly in the Windows background without any terminal or batch files.

Features:
- Unified Single-Stream Architecture: Rock-solid stability on Windows DirectSound
- Wake-Word Engine:
    * Real-time acoustic phrase transcription strictly for 'Hey Nexus', 'Nexus'
- DirectSound microphone auto-probing: Guaranteed active, unmuted microphone input
- Sub-10ms acoustic chime feedback on wake detection
- Clicky Windows Visual Screen Companion integration:
    * Pulsating glowing spotlight overlay over physical screen elements
    * On-screen status badges ("Listening...", "Executing...", "Speaking...")
    * Tray companion and mouse follower
- Vivo Office Kit cross-device bridge for iQOO 15 smartphone
- Local GGUF LLM reasoning + low-latency Windows desktop automation tools
"""

import os
import re
import sys
import time
import json
import logging
import threading
import collections
import audioop
import winsound
import ctypes
import keyboard
from pathlib import Path
from datetime import datetime

import numpy as np
import psutil
import pyaudio
import scipy.signal
import speech_recognition as sr
from openwakeword.model import Model as OWWModel

# Configure logging to disk
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
LOG_FILE = PROJECT_ROOT / "nexus_daemon.log"
PID_FILE = PROJECT_ROOT / "nexus_daemon.pid"

# Safe stdout/stderr redirection for headless/windowless daemon execution
try:
    if sys.stdout is None:
        sys.stdout = open(str(LOG_FILE), "a", encoding="utf-8", buffering=1)
    else:
        sys.stdout.write("")
except Exception:
    sys.stdout = open(str(LOG_FILE), "a", encoding="utf-8", buffering=1)

try:
    if sys.stderr is None:
        sys.stderr = open(str(LOG_FILE), "a", encoding="utf-8", buffering=1)
    else:
        sys.stderr.write("")
except Exception:
    sys.stderr = open(str(LOG_FILE), "a", encoding="utf-8", buffering=1)

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("NexusDaemon")


def handle_exception(exc_type, exc_value, exc_traceback):
    logger.critical("UNHANDLED EXCEPTION in main thread:", exc_info=(exc_type, exc_value, exc_traceback))


def handle_thread_exception(args):
    logger.critical(f"UNHANDLED EXCEPTION in thread {args.thread}:", exc_info=(args.exc_type, args.exc_value, args.exc_traceback))


sys.excepthook = handle_exception
threading.excepthook = handle_thread_exception

sys.path.insert(0, str(CURRENT_DIR))

from jarvis_tools import JarvisTools
from jarvis_voice import JarvisTTS, get_best_audio_input
from jarvis_brain import JarvisBrain
from clicky_bridge import clicky
from nexus_routines import routines
from nexus_dictation import dictation
from nexus_browser import browser_agent
from nexus_personas import personas
from nexus_office_kit import office_kit


class NexusBackgroundDaemon:
    """Continuous background voice assistant daemon for Windows."""

    def __init__(self):
        self.tts = JarvisTTS(rate=175, volume=1.0)
        self.brain = JarvisBrain(use_llm=True)
        self.recognizer = sr.Recognizer()

        self.dev_index, self.dev_rate, self.dev_name = get_best_audio_input()
        logger.info(f"Nexus initialized on microphone: [{self.dev_index}] {self.dev_name} @ {self.dev_rate}Hz")

        # Wire subsystem dependencies
        dictation.tts = self.tts
        dictation.clicky = clicky
        dictation.brain = self.brain

        browser_agent.clicky = clicky
        browser_agent.brain = self.brain
        browser_agent.tts = self.tts

        routines.tts = self.tts
        routines.clicky = clicky

        # OpenWakeWord hey_jarvis removed per user request: assistant is strictly Nexus
        self.oww = None

        self._is_busy = False
        self._running = True

    def _play_wake_chime(self):
        """Plays immediate acoustic chime for wake confirmation (< 10ms)."""
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass

    def _parse_wake_command(self, transcript: str):
        """Checks for 'Hey Nexus', 'Nexus' and extracts command, strictly rejecting 'Jarvis'."""
        t = transcript.lower().strip()
        t_clean = re.sub(r"[^\w\s]", " ", t)
        t_clean = " ".join(t_clean.split())

        # Explicitly reject any Jarvis mentions
        if "jarvis" in t_clean:
            return False, ""

        # High-confidence pattern matching for Nexus phonetic variations
        prefix = r"(?:(?:hey|hi|hello|ok|okay)\s+)?"
        wake_words = r"(?:nexus|nexas|nexis|lexus|texas|next\s+us|next\s+is|necks\s+us)"

        match = re.search(rf"^{prefix}{wake_words}\b\s*(.*)$", t_clean)
        if match:
            cmd = match.group(1).strip()
            return True, cmd

        # Also capture "Hey access", "Hey axis" when preceded by wake word greeting
        access_match = re.search(r"^(?:hey|hi|hello|ok|okay)\s+(?:access|axis)\b\s*(.*)$", t_clean)
        if access_match:
            cmd = access_match.group(1).strip()
            return True, cmd

        # Wake word anywhere at the beginning of phrase
        wake_search = re.search(rf"\b{wake_words}\b", t_clean)
        if wake_search and wake_search.start() < 18:
            cmd = t_clean[wake_search.end():].strip()
            return True, cmd

        return False, ""

    def start(self):
        """Starts background daemon, Clicky companion overlay, and unified audio listener."""
        # Single-instance enforcement: if already running, focus/expand Notch HUD and exit cleanly
        if PID_FILE.exists():
            try:
                old_pid = int(PID_FILE.read_text().strip())
                if old_pid != os.getpid() and psutil.pid_exists(old_pid):
                    p = psutil.Process(old_pid)
                    if "python" in p.name().lower():
                        logger.info(f"Nexus daemon is already running (PID {old_pid}). Expanding Notch HUD and exiting duplicate.")
                        clicky.expand_notch()
                        sys.exit(0)
            except Exception:
                pass

        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))

        logger.info(f"Nexus daemon started with PID {os.getpid()}")

        # Ensure Clicky Windows visual companion overlay is running
        try:
            clicky.ensure_clicky_running()
        except Exception as ce:
            logger.warning(f"Could not initialize Clicky companion: {ce}")

        # Start Vivo Office Kit bidirectional bridge
        try:
            self._start_office_kit()
        except Exception as oke:
            logger.warning(f"Office Kit bridge could not start: {oke}")

        # Start Windows + Alt physical global hotkey listener
        self._start_hotkey_listener()

        # Start persistent routine scheduler with sleeping-machine catchup
        routines.start()
        clicky.set_routine_status(routines.get_status_summary())

        # Start full-duplex Clicky Notch UI event listener
        try:
            clicky.start_listener(self._handle_incoming_clicky_message)
        except Exception as cle:
            logger.warning(f"Could not engage Clicky incoming listener: {cle}")

        # Announce readiness
        self._play_wake_chime()
        self.tts.speak("Nexus online. Standing by in the background. Call me anytime with Hey Nexus.")

        # Run Unified Audio Stream Loop on main thread
        try:
            self._unified_audio_stream_loop()
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            self._running = False
            if PID_FILE.exists():
                PID_FILE.unlink(missing_ok=True)
            logger.info("Nexus daemon stopped.")

    def _start_hotkey_listener(self):
        """
        Listens for the physical 'Windows + Alt' (or Win + Alt) key combination
        system-wide without requiring any active console window.
        Uses dual-engine detection: low-level keyboard hook + hardware GetAsyncKeyState poller.
        """
        logger.info("Initializing Windows + Alt global hotkey listener...")

        last_press_time = [0.0]
        press_timer = [None]

        def _on_hotkey_press():
            now = time.time()
            dt = now - last_press_time[0]
            last_press_time[0] = now

            if dt < 0.45:
                # Double-tap detected: Direct Hands-Free Dictation Activation (Workflow 13)
                if press_timer[0] is not None:
                    press_timer[0].cancel()
                    press_timer[0] = None
                logger.info("[HOTKEY DOUBLE-TAP DETECTED] Activating Hands-Free Dictation Mode!")
                self._handle_wake_event(command="start dictation")
            else:
                # Single tap: expand notch and listen for command
                def _trigger_single():
                    logger.info("[PHYSICAL HOTKEY TRIGGERED] Windows + Alt pressed!")
                    clicky.expand_notch()
                    self._handle_wake_event(command="")

                press_timer[0] = threading.Timer(0.35, _trigger_single)
                press_timer[0].start()

        # Engine 1: Low-level keyboard hook
        try:
            keyboard.add_hotkey("windows+alt", _on_hotkey_press, suppress=False)
            logger.info("Low-level OS keyboard hook engaged for Windows + Alt.")
        except Exception as e:
            logger.warning(f"Could not bind keyboard.add_hotkey: {e}")

        # Engine 2: Hardware GetAsyncKeyState poller (failsafe across elevated windows)
        def _poll_async_keystates():
            user32 = ctypes.windll.user32
            VK_LWIN = 0x5B
            VK_RWIN = 0x5C
            VK_MENU = 0x12  # Alt

            was_pressed = False
            while self._running:
                try:
                    win_down = bool((user32.GetAsyncKeyState(VK_LWIN) & 0x8000) or (user32.GetAsyncKeyState(VK_RWIN) & 0x8000))
                    alt_down = bool(user32.GetAsyncKeyState(VK_MENU) & 0x8000)
                    is_pressed = win_down and alt_down

                    if is_pressed and not was_pressed:
                        was_pressed = True
                        _on_hotkey_press()
                    elif not is_pressed and was_pressed:
                        was_pressed = False
                except Exception:
                    pass
                try:
                    time.sleep(0.02)  # 20ms polling interval
                except OSError:
                    time.sleep(0.05)  # Backoff on WinError 1450 (Insufficient system resources)

        poll_thread = threading.Thread(target=_poll_async_keystates, daemon=True)
        poll_thread.start()
        logger.info("Physical hardware GetAsyncKeyState poller engaged for Windows + Alt.")


    def _unified_audio_stream_loop(self):
        """
        Unified Single-Stream Capture with Auto-Recovery Watchdog and Adaptive EMA noise floor:
        Processes 1024-sample chunks from the active microphone.
        Simultaneously runs:
        1. OpenWakeWord neural inference for 'Hey Jarvis' (< 15ms)
        2. Speech phrase accumulation and recognition for 'Hey Nexus' & commands
        """
        while self._running:
            p = pyaudio.PyAudio()
            try:
                dev_info = p.get_device_info_by_index(self.dev_index)
                max_ch = int(dev_info.get("maxInputChannels", 1))
                channels = min(max_ch, 2)
            except Exception:
                channels = 1
            chunk_size = 1024

            try:
                stream = p.open(
                    format=pyaudio.paInt16,
                    channels=channels,
                    rate=self.dev_rate,
                    input=True,
                    input_device_index=self.dev_index,
                    frames_per_buffer=chunk_size
                )
            except Exception as e:
                logger.error(f"Failed to open primary audio capture stream: {e}. Re-probing in 2s...")
                p.terminate()
                time.sleep(2.0)
                self.dev_index, self.dev_rate, self.dev_name = get_best_audio_input()
                continue

            # Flush startup buffer transients (discard 10 chunks ~ 0.23s)
            for _ in range(10):
                try:
                    stream.read(chunk_size, exception_on_overflow=False)
                except Exception:
                    pass

            # Ambient noise floor calibration (median-filtered across 25 chunks)
            logger.info(f"Calibrating ambient noise floor on live stream (device [{self.dev_index}] {self.dev_name}, {channels}ch)...")
            ambient_samples = []
            for _ in range(25):  # ~0.58 seconds
                try:
                    raw = stream.read(chunk_size, exception_on_overflow=False)
                    if channels == 2:
                        mono_raw = audioop.tomono(raw, 2, 0.5, 0.5)
                    else:
                        mono_raw = raw
                    rms = audioop.rms(mono_raw, 2)
                    ambient_samples.append(rms)
                except Exception:
                    pass

            if ambient_samples:
                sorted_samples = sorted(ambient_samples)
                median_noise = sorted_samples[len(sorted_samples) // 2]
                avg_noise = min(max(median_noise, 50.0), 1200.0)
            else:
                avg_noise = 400.0

            # Set speech threshold adaptively: bound strictly in [300.0, 1800.0]
            speech_threshold = min(max(avg_noise * 1.45, 300.0), 1800.0)
            logger.info(f"Calibration complete: Ambient Noise={avg_noise:.1f}, Speech Threshold={speech_threshold:.1f}")

            # Stream state with acoustic pre-roll ring buffer (~320ms / 14 chunks)
            pre_roll_buffer = collections.deque(maxlen=14)
            speech_frames = []
            is_speaking = False
            silence_chunks = 0
            max_silence_chunks = int(0.7 * (self.dev_rate / chunk_size))  # ~0.7s of silence ends phrase
            max_phrase_chunks = int(8.0 * (self.dev_rate / chunk_size))   # 8s max phrase length
            min_phrase_bytes = int(0.35 * self.dev_rate * 2)              # 0.35s minimum phrase length

            logger.info("Unified background voice listener engaged.")

            try:
                while self._running:
                    if self._is_busy:
                        # Discard audio while speaking / executing tools
                        try:
                            stream.read(chunk_size, exception_on_overflow=False)
                        except Exception:
                            pass
                        time.sleep(0.05)
                        pre_roll_buffer.clear()
                        continue

                    try:
                        raw_chunk = stream.read(chunk_size, exception_on_overflow=False)
                        if channels == 2:
                            mono_chunk = audioop.tomono(raw_chunk, 2, 0.5, 0.5)
                        else:
                            mono_chunk = raw_chunk
                    except Exception as re_err:
                        logger.debug(f"Audio read glitch: {re_err}")
                        break

                    chunk_rms = audioop.rms(mono_chunk, 2)

                    # When not actively speaking, buffer chunks in pre-roll and adapt noise floor
                    if not is_speaking:
                        pre_roll_buffer.append(mono_chunk)
                        if chunk_rms <= speech_threshold:
                            # Dynamic fast downward, slow upward adaptation
                            if chunk_rms < avg_noise:
                                avg_noise = avg_noise * 0.90 + chunk_rms * 0.10
                            else:
                                avg_noise = avg_noise * 0.995 + chunk_rms * 0.005
                            speech_threshold = min(max(avg_noise * 1.45, 300.0), 1800.0)

                    # Continuous Acoustic Voice Activity & Phrase Accumulation
                    if chunk_rms > speech_threshold:
                        if not is_speaking:
                            is_speaking = True
                            # Prepend pre-roll buffer so the leading consonant / "Hey" is fully preserved!
                            speech_frames = list(pre_roll_buffer)
                            speech_frames.append(mono_chunk)
                            silence_chunks = 0
                        else:
                            speech_frames.append(mono_chunk)
                    elif is_speaking:
                        speech_frames.append(mono_chunk)
                        silence_chunks += 1
                        if silence_chunks >= max_silence_chunks or len(speech_frames) >= max_phrase_chunks:
                            # Completed utterance detected
                            full_audio_bytes = b"".join(speech_frames)
                            speech_frames = []
                            is_speaking = False
                            silence_chunks = 0
                            pre_roll_buffer.clear()

                            # Process if utterance exceeds minimum speech duration
                            if len(full_audio_bytes) >= min_phrase_bytes:
                                threading.Thread(
                                    target=self._process_active_command,
                                    args=(full_audio_bytes,),
                                    daemon=True
                                ).start()
            except Exception as stream_err:
                logger.error(f"Stream processing error: {stream_err}")
            finally:
                try:
                    stream.stop_stream()
                    stream.close()
                    p.terminate()
                except Exception:
                    pass

    def _process_active_command(self, raw_audio: bytes):
        """Transcribes accumulated speech and triggers command if wake word is detected."""
        try:
            audio_data = sr.AudioData(raw_audio, self.dev_rate, 2)
            transcript = self.recognizer.recognize_google(audio_data)
            logger.info(f"Heard speech snippet: '{transcript}'")
        except sr.UnknownValueError:
            return
        except Exception as e:
            logger.debug(f"Speech recognition error: {e}")
            return

        # Check if we were actively waiting for a follow-up command after wake
        if getattr(self, "_awaiting_follow_up", False):
            if time.time() < getattr(self, "_follow_up_deadline", 0):
                self._awaiting_follow_up = False
                logger.info(f"[FOLLOW-UP COMMAND RECEIVED]: '{transcript}'")
                self._handle_wake_event(command=transcript)
                return
            else:
                self._awaiting_follow_up = False

        woke, command = self._parse_wake_command(transcript)
        if not woke:
            return

        logger.info(f"[WAKE TRIGGERED via SpeechRecognition] Transcript: '{transcript}' | Command: '{command}'")
        self._handle_wake_event(command=command)

    def _execute_routed_command(self, command: str) -> bool:
        """
        Evaluates command against specialized Nexus voice workflows.
        Returns True if command was handled (stops LLM fallback).
        """
        lower_cmd = command.lower().strip()
        tools = JarvisTools()

        # ── App Launch ──────────────────────────────────────────────────────────
        # "open chrome", "launch vscode", "open calculator"
        open_match = re.match(
            r"^(?:open|launch|start|run|load|bring up|fire up)\s+(.+)$", lower_cmd
        )
        if open_match:
            app_name = open_match.group(1).strip()
            # Strip trailing noise words
            app_name = re.sub(r"\s*(please|now|for me|up)\s*$", "", app_name).strip()
            clicky.set_stage("reading", f"Opening {app_name}...")
            result = tools.launch_app(app_name)
            if result.get("status") == "success":
                self.tts.speak(f"Opening {app_name}.")
            else:
                self.tts.speak(f"I couldn't find {app_name}. Make sure it's installed.")
                logger.warning(f"[APP LAUNCH FAILED]: {app_name} — {result}")
            return True

        # ── Close App ────────────────────────────────────────────────────────────
        close_match = re.match(r"^(?:close|quit|kill|exit)\s+(.+)$", lower_cmd)
        if close_match:
            app_name = close_match.group(1).strip()
            self.tts.speak(f"Closing {app_name}.")
            subprocess.Popen(f"taskkill /F /IM {app_name}.exe", shell=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True

        # ── Screenshot ───────────────────────────────────────────────────────────
        if any(kw in lower_cmd for kw in ["take a screenshot", "capture screen", "screenshot"]):
            self.tts.speak("Taking screenshot.")
            result = tools.take_screenshot()
            path = result.get("path", "")
            self.tts.speak(f"Screenshot saved." if path else "Screenshot failed.")
            return True

        # ── Volume control ───────────────────────────────────────────────────────
        if any(kw in lower_cmd for kw in ["volume up", "increase volume", "louder"]):
            for _ in range(3):
                pyautogui.press("volumeup")
            self.tts.speak("Volume increased.")
            return True
        if any(kw in lower_cmd for kw in ["volume down", "decrease volume", "quieter", "lower the volume"]):
            for _ in range(3):
                pyautogui.press("volumedown")
            self.tts.speak("Volume decreased.")
            return True
        if any(kw in lower_cmd for kw in ["mute", "silence", "unmute"]):
            pyautogui.press("volumemute")
            self.tts.speak("Toggled mute.")
            return True

        # ── System control ───────────────────────────────────────────────────────
        if any(kw in lower_cmd for kw in ["lock screen", "lock the screen", "lock computer"]):
            self.tts.speak("Locking screen. Goodbye Sir.")
            subprocess.Popen("rundll32.exe user32.dll,LockWorkStation", shell=True)
            return True
        if any(kw in lower_cmd for kw in ["sleep", "put to sleep", "hibernate"]):
            self.tts.speak("Putting your system to sleep. Goodnight Sir.")
            time.sleep(1.5)
            subprocess.Popen("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
            return True
        if any(kw in lower_cmd for kw in ["shutdown", "turn off", "power off"]):
            self.tts.speak("Initiating shutdown. Goodbye Sir.")
            time.sleep(2)
            subprocess.Popen("shutdown /s /t 5", shell=True)
            return True
        if any(kw in lower_cmd for kw in ["restart", "reboot"]):
            self.tts.speak("Restarting your system.")
            time.sleep(2)
            subprocess.Popen("shutdown /r /t 5", shell=True)
            return True

        # ── Open URL / website ───────────────────────────────────────────────────
        url_match = re.match(
            r"^(?:go to|open|visit|navigate to|browse to)\s+(https?://\S+|www\.\S+|\S+\.\w{2,})$",
            lower_cmd
        )
        if url_match:
            url = url_match.group(1)
            if not url.startswith("http"):
                url = "https://" + url
            self.tts.speak(f"Opening {url}.")
            import webbrowser
            webbrowser.open(url)
            return True

        # ── What time is it / date ────────────────────────────────────────────────
        if any(kw in lower_cmd for kw in ["what time", "current time", "what's the time"]):
            now = datetime.now().strftime("%I:%M %p")
            self.tts.speak(f"The time is {now}.")
            return True
        if any(kw in lower_cmd for kw in ["what date", "today's date", "what day"]):
            today = datetime.now().strftime("%A, %B %d, %Y")
            self.tts.speak(f"Today is {today}.")
            return True

        # ── Persona Switching ─────────────────────────────────────────────────────
        if any(kw in lower_cmd for kw in ["switch to", "switch persona to", "change persona to"]):
            for p_key in ["coder", "teacher", "researcher", "nexus"]:
                if p_key in lower_cmd:
                    res = personas.switch_persona(p_key)
                    clicky.set_persona(p_key)
                    self.tts.speak(f"Switched persona to {res['name']}. {res['role']} at your service.")
                    return True

        # ── Dictation & Screen-aware drafting ─────────────────────────────────────
        if "start dictation" in lower_cmd or "dictate" in lower_cmd:
            self.tts.speak("Dictation mode active. Speak your text.")
            clicky.set_stage("listening", "Dictating...")
            try:
                mic = sr.Microphone(device_index=self.dev_index)
                with mic as source:
                    audio = self.recognizer.listen(source, timeout=8.0, phrase_time_limit=15.0)
                    text = self.recognizer.recognize_google(audio)
                    dictation.type_text(text)
                    self.tts.speak("Typed into active window.")
            except Exception as de:
                logger.info(f"Dictation timeout: {de}")
            return True

        if "draft" in lower_cmd and any(kw in lower_cmd for kw in ["reply", "email", "message"]):
            self.tts.speak("Analyzing active screen to draft response...")
            dictation.draft_screen_aware(command)
            return True

        # ── Web Research & Browser-Use ────────────────────────────────────────────
        if any(kw in lower_cmd for kw in ["search for", "research", "search the web for", "browse to"]):
            query = re.sub(
                r"^(?:search for|research|search the web for|browse to)\s+", "",
                lower_cmd, flags=re.IGNORECASE
            )
            self.tts.speak(f"Researching {query}...")
            browser_agent.search_and_research(query)
            return True

        # ── Routines ──────────────────────────────────────────────────────────────
        if "run routine" in lower_cmd or "execute routine" in lower_cmd:
            for r_id in ["morning_briefing", "git_watch_summary", "cache_hygiene"]:
                if r_id.replace("_", " ") in lower_cmd or r_id in lower_cmd:
                    self.tts.speak(f"Executing routine {r_id}...")
                    routines.execute_routine(r_id)
                    return True
        if any(kw in lower_cmd for kw in ["check routine", "what are my routines", "routine status"]):
            status = routines.get_status_summary()
            self.tts.speak(f"Your routines are running. {status}.")
            clicky.set_routine_status(status)
            return True

        # Workflow: Application Launch
        for prefix in ["open ", "launch ", "start "]:
            if lower_cmd.startswith(prefix):
                app_name = lower_cmd.replace(prefix, "").strip()
                if app_name:
                    self.tts.speak(f"Opening {app_name}.")
                    JarvisTools.launch_app(app_name)
                    return True

        return False



    def _handle_wake_event(self, command: str = ""):
        """Central wake execution: chimes, expands Notch HUD, and processes query."""
        if self._is_busy:
            return

        self._is_busy = True
        try:
            self._play_wake_chime()
            clicky.expand_notch()
            clicky.set_stage("listening", "Listening to you...")

            if command:
                logger.info(f"[ONE-SHOT COMMAND]: '{command}'")
                clicky.set_stage("reading", "Executing...")
                if not self._execute_routed_command(command):
                    speech_reply, tool_res = self.brain.process_query(command)
                    clicky.set_stage("speaking", "Speaking...")
                    self.tts.speak(speech_reply)
                    if tool_res:
                        logger.info(f"Executed tool: {tool_res}")
            else:
                logger.info("[WAKE WORD ONLY TRIGGERED] Expanding Notch HUD and standing by for follow-up.")
                self.tts.speak("At your service, Sir. How can I assist you?")
                self._awaiting_follow_up = True
                self._follow_up_deadline = time.time() + 10.0
        finally:
            clicky.set_stage("done", "")
            time.sleep(0.5)
            self._is_busy = False

    def _start_office_kit(self):
        """
        Wire up the Vivo Office Kit bidirectional bridge.
        Handles all incoming events from the iQOO 15 and routes tasks to the LLM.
        """
        def _handle_phone_task(task: dict) -> str:
            """Process a TaskDescriptor from the phone through local LLM + tools."""
            task_type   = task.get("type", "LONG_CONTEXT_ANALYSIS")
            instruction = task.get("instruction", "Analyze the provided input.")
            payload     = task.get("payload", "")

            clicky.set_stage("reading", f"📱 Phone task: {instruction[:40]}...")
            self.tts.speak(f"Sir, processing escalated task from your iQOO 15. {instruction[:60]}.")

            if task_type == "WEB_LOOKUP":
                result = browser_agent.search_and_research(instruction)
                return result or f"Web research complete for: {instruction}"
            elif task_type == "ROUTINE_TRIGGER":
                r_id = task.get("payload", {}).get("routine_id", "morning_briefing") if isinstance(task.get("payload"), dict) else "morning_briefing"
                routines.execute_routine(r_id)
                return f"Routine '{r_id}' triggered from iQOO 15."
            else:
                # Default: send to local LLM
                full_prompt = f"{instruction}\n\nContext:\n{payload}" if payload else instruction
                speech_reply, tool_res = self.brain.process_query(full_prompt)
                if tool_res:
                    return f"{speech_reply}\n\nTool result: {tool_res}"
                return speech_reply

        def _handle_phone_event(event: dict):
            """React to non-task phone events (battery, connect, status, etc.)."""
            action  = event.get("action", "")
            payload = event.get("payload", {})

            if action == "PHONE_CONNECTED":
                phone_name = payload.get("device", "iQOO 15")
                logger.info(f"[Office Kit] {phone_name} CONNECTED")
                clicky.set_phone_status("connected", phone_name)
                self._play_wake_chime()
                self.tts.speak(f"Sir, your {phone_name} has connected through Office Kit. Cross-device bridge is online.")

            elif action == "PHONE_DISCONNECTED":
                logger.info("[Office Kit] iQOO 15 DISCONNECTED")
                clicky.set_phone_status("disconnected", "iQOO 15")
                self.tts.speak("Your iQOO 15 has disconnected from the Office Kit bridge.")

            elif action == "PHONE_BATTERY_LOW":
                level = payload.get("level", "?")
                logger.info(f"[Office Kit] iQOO 15 battery low: {level}%")
                clicky.set_phone_status("battery_low", f"iQOO 15 – {level}%")
                self.tts.speak(f"Warning, Sir. Your iQOO 15 battery is at {level} percent. Please plug in.")

            elif action == "CAPTURE_RESULT":
                filename = payload.get("filename", "photo")
                logger.info(f"[Office Kit] File received from phone: {filename}")
                self.tts.speak(f"File received from your phone: {filename}.")

            elif action == "STATUS_PING":
                # Phone is checking if laptop is alive; reply with ACK
                office_kit.send_to_phone("STATUS_ACK", {
                    "status": "ONLINE",
                    "daemon": "NexusLaptop",
                    "pid":    os.getpid(),
                })
                logger.info("[Office Kit] STATUS_PING → replied with STATUS_ACK")

            elif action == "HANDOFF_REQUEST":
                # Legacy format — route as task
                text = payload.get("text", "New request from phone") if isinstance(payload, dict) else str(payload)
                task = {"id": event.get("id", f"hndff_{int(time.time())}"),
                        "type": "LONG_CONTEXT_ANALYSIS",
                        "instruction": text, "payload": ""}
                result = _handle_phone_task(task)
                self.tts.speak(result[:200] if result else "Done.")

        # Wire the callbacks into the OfficeKitBridge singleton
        office_kit._on_task  = _handle_phone_task
        office_kit._on_event = _handle_phone_event
        office_kit.start()
        logger.info("Vivo Office Kit Bridge fully wired and running.")

    def _handle_incoming_clicky_message(self, msg: dict):
        """Processes real-time UI interaction events sent from the Clicky Notch HUD."""
        action = msg.get("action")
        if action == "client_action":
            sub = msg.get("subaction", "")
            logger.info(f"[CLICKY UI ACTION TRIGGERED]: {sub}")
            if sub == "talk":
                self._handle_wake_event(command="")
            elif sub == "dictate":
                self._handle_wake_event(command="start dictation")
            elif sub == "browse":
                self._handle_wake_event(command="search for latest technology news")
            elif sub.startswith("run_routine:"):
                r_id = sub.split(":", 1)[1]
                logger.info(f"[CLICKY UI RUN ROUTINE]: {r_id}")
                self.tts.speak(f"Triggering {r_id.replace('_', ' ')} routine.")
                routines.execute_routine(r_id)
                clicky.set_routine_status(routines.get_status_summary())
            elif sub == "query":
                q = msg.get("text", "")
                if q:
                    self._handle_wake_event(command=q)
        elif action == "switch_persona":
            target = msg.get("persona", "nexus")
            logger.info(f"[CLICKY UI SWITCH PERSONA]: {target}")
            res = personas.switch_persona(target)
            clicky.set_persona(target)
            self.tts.speak(f"Switched persona to {res['name']}.")
        elif action == "user_query":
            q = msg.get("query", "")
            if q:
                logger.info(f"[CLICKY UI USER QUERY]: {q}")
                self._handle_wake_event(command=q)


if __name__ == "__main__":
    daemon = NexusBackgroundDaemon()
    daemon.start()
