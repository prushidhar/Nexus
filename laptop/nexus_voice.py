"""
Real-time Voice Pipeline: OpenWakeWord Detection + SpeechRecognition + pyttsx3 Synthesis.
100% on-device wake detection and low-latency voice capture/synthesis for Desktop Nexus.
"""

import sys
import time
import queue
import logging
import threading
from typing import Optional, Callable, Tuple

import audioop
import numpy as np
import pyaudio
import pyttsx3
import scipy.signal
import speech_recognition as sr
import openwakeword
from openwakeword.model import Model as OWWModel

logger = logging.getLogger("NexusVoice")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def get_best_audio_input() -> Tuple[int, int, str]:
    """
    Auto-discovers the best working Windows microphone input device.
    Prioritizes Windows Primary Sound Capture Driver (DirectSound multiplexer),
    properly flushing hardware buffer transients across multi-chunk probes.
    """
    p = pyaudio.PyAudio()
    best_index = 0
    best_rate = 44100
    best_name = "Default"

    try:
        candidates = []
        ds_primary = None
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info.get("maxInputChannels", 0) > 0:
                candidates.append((i, info))
                name_lower = info.get("name", "").lower()
                hostapi = info.get("hostApi", -1)
                if (hostapi == 1 or "directsound" in str(info)) and "primary sound capture" in name_lower:
                    ds_primary = (i, info)

        # 1. First probe Windows Primary Sound Capture Driver
        if ds_primary:
            i, info = ds_primary
            rate = int(info.get("defaultSampleRate", 44100))
            channels = min(int(info.get("maxInputChannels", 1)), 2)
            try:
                stream = p.open(
                    format=pyaudio.paInt16,
                    channels=channels,
                    rate=rate,
                    input=True,
                    input_device_index=i,
                    frames_per_buffer=1024
                )
                # Flush first 2 transient chunks
                for _ in range(2):
                    stream.read(1024, exception_on_overflow=False)
                # Test 3 real audio chunks
                rms_vals = []
                for _ in range(3):
                    raw = stream.read(1024, exception_on_overflow=False)
                    mono = audioop.tomono(raw, 2, 0.5, 0.5) if channels == 2 else raw
                    rms_vals.append(audioop.rms(mono, 2))
                stream.stop_stream()
                stream.close()
                ints = [int.from_bytes(mono[j:j+2], 'little', signed=True) for j in range(0, min(len(mono), 256), 2)]
                if len(set(ints)) > 4 and rms_vals and (sum(rms_vals) / len(rms_vals)) > 5:
                    logger.info(f"Selected Windows Primary DirectSound Capture: [{i}] {info.get('name')} @ {rate}Hz")
                    p.terminate()
                    return i, rate, info.get("name", "Primary Sound Capture Driver")
            except Exception as e:
                logger.debug(f"DirectSound primary probe error: {e}")

        # 2. Multi-sample probe across candidate input devices
        best_score = -1.0
        for i, info in candidates:
            name = info.get("name", "")
            hostapi = info.get("hostApi", -1)
            rate = int(info.get("defaultSampleRate", 44100))
            channels = min(int(info.get("maxInputChannels", 1)), 2)
            is_ds = hostapi == 1

            try:
                stream = p.open(
                    format=pyaudio.paInt16,
                    channels=channels,
                    rate=rate,
                    input=True,
                    input_device_index=i,
                    frames_per_buffer=1024
                )
                # Flush 2 transient chunks
                for _ in range(2):
                    stream.read(1024, exception_on_overflow=False)
                rms_vals = []
                for _ in range(3):
                    raw = stream.read(1024, exception_on_overflow=False)
                    if channels == 2:
                        mono = audioop.tomono(raw, 2, 0.5, 0.5)
                    else:
                        mono = raw
                    rms_vals.append(audioop.rms(mono, 2))
                stream.stop_stream()
                stream.close()

                avg_rms = sum(rms_vals) / max(len(rms_vals), 1)
                score = avg_rms + (200 if is_ds else 0)
                ints = [int.from_bytes(mono[j:j+2], 'little', signed=True) for j in range(0, min(len(mono), 256), 2)]
                distinct_samples = len(set(ints))
                if distinct_samples > 4 and score > best_score and avg_rms > 5:
                    best_score = score
                    best_index = i
                    best_rate = rate
                    best_name = name
            except Exception:
                pass

        if best_score > 0:
            logger.info(f"Selected active microphone with live audio: [{best_index}] {best_name} @ {best_rate}Hz (score={best_score:.1f})")
            p.terminate()
            return best_index, best_rate, best_name

        # Fallback: Default input device
        default_info = p.get_default_input_device_info()
        best_index = int(default_info.get("index", 0))
        best_rate = int(default_info.get("defaultSampleRate", 44100))
        best_name = default_info.get("name", "Default")
    except Exception as e:
        logger.warning(f"Error querying input devices: {e}")
    finally:
        try:
            p.terminate()
        except Exception:
            pass

    return best_index, best_rate, best_name


def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except Exception:
        pass


class NexusTTS:
    """Thread-safe Text-to-Speech synthesizer using Windows SAPI5."""

    def __init__(self, rate: int = 175, volume: float = 1.0):
        self.rate = rate
        self.volume = volume
        self._lock = threading.Lock()

    def speak(self, text: str, wait: bool = True):
        """Speaks text aloud through primary audio device and prints transcript."""
        clean_text = text.strip()
        if not clean_text:
            return

        safe_print(f"\n\033[96m[NEXUS SPEAKING]\033[0m: {clean_text}\n")
        
        with self._lock:
            try:
                engine = pyttsx3.init("sapi5")
                engine.setProperty("rate", self.rate)
                engine.setProperty("volume", self.volume)
                voices = engine.getProperty("voices")
                for v in voices:
                    if "david" in v.name.lower():
                        engine.setProperty("voice", v.id)
                        break
                engine.say(clean_text)
                engine.runAndWait()
                engine.stop()
            except Exception as e:
                logger.error(f"TTS speak error: {e}")


class NexusASR:
    """Microphone listener and Speech-to-Text transcriber."""

    def __init__(self, mic_index: Optional[int] = None):
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = 1.5
        self.recognizer.pause_threshold = 0.6
        self.recognizer.non_speaking_duration = 0.3
        
        if mic_index is not None:
            self.mic_index = mic_index
        else:
            idx, _, name = get_best_audio_input()
            self.mic_index = idx
            logger.info(f"Initialized ASR with Microphone: [{idx}] {name}")

        self._calibrated = False

    def calibrate(self):
        """Calibrates energy threshold to the current room noise floor."""
        try:
            mic = sr.Microphone(device_index=self.mic_index)
            with mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.8)
            self._calibrated = True
            logger.info(f"ASR calibrated to ambient noise threshold: {self.recognizer.energy_threshold:.1f}")
        except Exception as e:
            logger.warning(f"Ambient noise calibration warning: {e}")

    def listen(self, timeout: float = 6.0, phrase_limit: float = 10.0) -> str:
        """Listens to the microphone and returns the transcribed text."""
        try:
            mic = sr.Microphone(device_index=self.mic_index)
        except Exception:
            mic = sr.Microphone()

        try:
            with mic as source:
                if not self._calibrated:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    self._calibrated = True
                safe_print("\033[92m[*] Listening to your voice... (speak now)\033[0m")
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
                safe_print("\033[93m[*] Audio captured, transcribing speech...\033[0m")
                
                transcript = self.recognizer.recognize_google(audio)
                safe_print(f"\033[97m[USER SAID]\033[0m: \"{transcript}\"")
                return transcript.strip()
        except sr.WaitTimeoutError:
            safe_print("[ASR] No speech detected (timeout).")
            return ""
        except sr.UnknownValueError:
            safe_print("[ASR] Could not understand the audio.")
            return ""
        except Exception as e:
            logger.error(f"ASR error: {e}")
            return ""


class NexusWakeDetector:
    """Continuous wake-word detection using openWakeWord neural model with hardware resampling."""

    TARGET_SAMPLE_RATE = 16000
    TARGET_CHUNK_SAMPLES = 1280  # 80ms at 16000Hz

    def __init__(self, threshold: float = 0.28, on_wake: Optional[Callable] = None):
        self.threshold = threshold
        self.on_wake = on_wake
        self._running = False
        self._paused = False
        self._thread = None
        
        self.dev_index, self.native_rate, self.dev_name = get_best_audio_input()
        self.native_chunk_size = int(self.native_rate * 0.080)  # exactly 80ms of audio
        logger.info(f"WakeDetector configured: [{self.dev_index}] {self.dev_name} ({self.native_rate}Hz, chunk={self.native_chunk_size})")

        logger.info("Loading openWakeWord neural model ('hey_jarvis')...")
        self.oww = OWWModel(wakeword_models=["hey_jarvis"], inference_framework="onnx")
        logger.info("openWakeWord model ready.")

    def pause(self):
        """Pauses wake-word listening during speech output or ASR recording."""
        self._paused = True

    def resume(self):
        """Resets neural buffer and resumes wake-word listening."""
        time.sleep(0.3)
        self.oww.reset()
        self._paused = False

    def start(self):
        """Starts background wake-word listening loop."""
        if self._running:
            return
        self._running = True
        self._paused = False
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Wake-word listener started in background.")

    def stop(self):
        """Stops background wake-word listening."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.info("Wake-word listener stopped.")

    def _run_loop(self):
        p = pyaudio.PyAudio()
        stream = None
        last_meter_time = 0
        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.native_rate,
                input=True,
                input_device_index=self.dev_index,
                frames_per_buffer=self.native_chunk_size
            )
            print(f"\033[95m[WAKE DETECTION ACTIVE]\033[0m Listening on [{self.dev_name}].")
            print("Say \033[1;32m'Hey Jarvis'\033[0m or press \033[1;36m[ENTER]\033[0m to command.\n")

            while self._running:
                if self._paused:
                    time.sleep(0.05)
                    continue

                data = stream.read(self.native_chunk_size, exception_on_overflow=False)
                if self._paused:
                    continue

                arr = np.frombuffer(data, dtype=np.int16)
                
                # Resample native audio (e.g. 44100Hz) to openWakeWord target (16000Hz)
                if self.native_rate != self.TARGET_SAMPLE_RATE:
                    resampled = scipy.signal.resample(arr, self.TARGET_CHUNK_SAMPLES).astype(np.int16)
                else:
                    resampled = arr

                # Calculate RMS audio energy for live feedback
                rms = float(np.sqrt(np.mean(resampled.astype(float)**2)))

                # Predict wake word activation scores
                prediction = self.oww.predict(resampled)
                score_jarvis = float(prediction.get("hey_jarvis", 0.0))

                # If sound is heard, print visual feedback so user sees mic is active
                now = time.time()
                if rms > 1500 and now - last_meter_time > 0.6:
                    bars = int(min(rms / 1000, 10))
                    meter = "#" * bars + "-" * (10 - bars)
                    print(f"\r\033[90m[MIC: {meter}] Level: {int(rms)} | Wake Score: {score_jarvis:.2f}\033[0m", end="", flush=True)
                    last_meter_time = now

                if score_jarvis >= self.threshold and not self._paused:
                    print(f"\n\n\033[92m[>>> WAKE WORD DETECTED: 'Hey Jarvis'! (Score: {score_jarvis:.2f}) <<<]\033[0m")
                    self._paused = True
                    self.oww.reset()
                    if self.on_wake:
                        self.on_wake()

        except Exception as e:
            logger.error(f"Wake loop exception: {e}")
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            p.terminate()


class NexusVoiceSubsystem:
    """Unified voice facade bundling TTS, ASR, and WakeWord detection."""

    def __init__(self):
        dev_idx, _, _ = get_best_audio_input()
        self.tts = NexusTTS()
        self.asr = NexusASR(mic_index=dev_idx)
        self.wake_detector = None

    def speak(self, text: str):
        self.tts.speak(text)

    def listen(self, timeout: float = 6.0, phrase_limit: float = 10.0) -> str:
        return self.asr.listen(timeout=timeout, phrase_limit=phrase_limit)

    def start_wake_listening(self, callback: Callable):
        self.wake_detector = NexusWakeDetector(on_wake=callback)
        self.wake_detector.start()

    def stop_wake_listening(self):
        if self.wake_detector:
            self.wake_detector.stop()

# Compatibility aliases
JarvisTTS = NexusTTS
JarvisASR = NexusASR
JarvisWakeDetector = NexusWakeDetector
JarvisVoiceSubsystem = NexusVoiceSubsystem
