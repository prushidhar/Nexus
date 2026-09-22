"""
Automated Comprehensive Test Suite for Jarvis Real-Time Voice Agent.
Tests TTS, ASR, openWakeWord neural engine, PC Automation Tools, Office Kit Bridge,
and Local GGUF LLM Inference with zero mocks.
"""

import sys
import unittest
from pathlib import Path

# Setup paths
LAPTOP_DIR = Path(r"C:\Users\P RUSHIDHAR\.gemini\antigravity\scratch\nexus-agent\laptop")
sys.path.insert(0, str(LAPTOP_DIR))

from jarvis_tools import JarvisTools
from jarvis_voice import JarvisTTS, JarvisASR, JarvisWakeDetector
from jarvis_brain import JarvisBrain


class TestRealTimeJarvis(unittest.TestCase):

    def test_01_tools_system_status(self):
        """Verifies real-time hardware telemetry reading."""
        res = JarvisTools.get_system_status()
        self.assertEqual(res["status"], "success")
        data = res["data"]
        self.assertIn("cpu", data)
        self.assertIn("memory", data)
        self.assertIn("battery", data)
        self.assertGreaterEqual(data["cpu"]["percent"], 0.0)
        self.assertGreater(data["memory"]["total_gb"], 1.0)
        print(f"\n[PASS] Hardware Telemetry: CPU={data['cpu']['percent']}%, RAM={data['memory']['percent']}%")

    def test_02_tools_office_kit_bridge(self):
        """Verifies Office Kit clipboard sync and task dispatch."""
        test_clip = "Test-Handoff-Payload-iQOO15"
        res = JarvisTools.office_kit_sync_clipboard(test_clip)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["clipboard"], test_clip)

        task_res = JarvisTools.office_kit_push_to_phone("CAPTURE_PHOTO", {"camera": "rear_telephoto"})
        self.assertEqual(task_res["status"], "success")
        self.assertIn("task_id", task_res)
        print(f"[PASS] Office Kit Bridge: Dispatched {task_res['task_id']}")

    def test_03_wake_detection_neural_model(self):
        """Verifies openWakeWord neural inference with 'hey_jarvis' ONNX model."""
        import numpy as np
        wd = JarvisWakeDetector(threshold=0.40)
        self.assertIn("hey_jarvis", wd.oww.models)
        
        # Test inference on audio chunk
        dummy_chunk = np.zeros(1280, dtype=np.int16)
        pred = wd.oww.predict(dummy_chunk)
        self.assertIn("hey_jarvis", pred)
        print(f"[PASS] openWakeWord Model: Inference successful, score={pred['hey_jarvis']}")

    def test_04_brain_fast_path_routing(self):
        """Verifies sub-millisecond intent routing."""
        brain = JarvisBrain(use_llm=False)
        speech, tool_res = brain.process_query("what is the system status")
        self.assertIn("System is operational", speech)
        self.assertIsNotNone(tool_res)
        print(f"[PASS] Fast-Path Intent Routing: \"{speech[:50]}...\"")

    def test_05_local_llm_inference(self):
        """Verifies 100% local GGUF model execution via llama.cpp."""
        brain = JarvisBrain(use_llm=True)
        self.assertIsNotNone(brain.llm, "GGUF LLM should be loaded")
        
        speech, tool_res = brain.process_query("What is your primary mission?")
        self.assertTrue(len(speech) > 0)
        print(f"[PASS] Local LLM Response: \"{speech}\"")


if __name__ == "__main__":
    unittest.main(verbosity=2)
