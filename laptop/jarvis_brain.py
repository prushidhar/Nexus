"""
Jarvis Reasoning Engine: Multi-layer Intelligence combining Fast-Path Intent Routing
and Local LLM Inference via llama.cpp (Qwen2.5-0.5B GGUF).
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from jarvis_tools import JarvisTools

logger = logging.getLogger("JarvisBrain")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

MODEL_PATH = Path(r"C:\Users\P RUSHIDHAR\.gemini\antigravity\scratch\nexus-agent\models\qwen2.5-0.5b-instruct-q4_k_m.gguf")


class JarvisBrain:
    """Core intelligence engine for understanding voice input and executing tools."""

    SYSTEM_PROMPT = (
        "You are Nexus, an elite real-time AI assistant for Windows PC and iQOO 15 smartphone. Your name is strictly Nexus.\n"
        "You control the PC through tools and coordinate mobile tasks via Vivo Office Kit.\n"
        "Keep answers concise, confident, and natural for voice synthesis (under 2 sentences).\n"
        "When an action is needed, output a single JSON action block like:\n"
        "```json\n"
        "{\"tool\": \"launch_app\", \"args\": {\"app_name\": \"chrome\"}, \"speech\": \"Launching Google Chrome for you, Sir.\"}\n"
        "```\n"
        "Available tools:\n"
        "- launch_app(app_name): opens chrome, notepad, vscode, calc, settings, terminal, spotify, etc.\n"
        "- system_status(): gets real-time CPU, RAM, battery, active window.\n"
        "- take_screenshot(): captures current screen display.\n"
        "- web_search(query): searches the web for a topic.\n"
        "- open_url(url): opens a specific website.\n"
        "- media_control(action): up, down, mute, playpause.\n"
        "- point_at_target(target): animates glowing spotlight on screen element (start menu, chrome, search, clock, etc.).\n"
        "- office_kit_sync(content): syncs clipboard with iQOO 15 phone.\n"
        "- push_to_phone(action, payload): dispatches mobile task to phone."
    )

    def __init__(self, use_llm: bool = True):
        self.llm = None
        self.use_llm = use_llm
        if self.use_llm and MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 400 * 1024 * 1024:
            self._init_llm()
        else:
            logger.info("LLM model pending download or disabled; operating on Fast-Path intent engine.")

    def _init_llm(self):
        try:
            import llama_cpp
            logger.info(f"Loading GGUF model into Llama engine: {MODEL_PATH.name}...")
            self.llm = llama_cpp.Llama(
                model_path=str(MODEL_PATH),
                n_ctx=2048,
                n_threads=6,
                verbose=False
            )
            logger.info("Local GGUF LLM engine loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load llama_cpp model: {e}")
            self.llm = None

    def think(self, prompt: str) -> str:
        """Direct text generation from the local GGUF model."""
        if self.llm is not None:
            try:
                output = self.llm.create_chat_completion(
                    messages=[
                        {"role": "system", "content": "You are Nexus, a helpful and precise assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=150,
                    temperature=0.3
                )
                return output["choices"][0]["message"]["content"].strip()
            except Exception as e:
                logger.error(f"LLM think error: {e}")
        speech, _ = self.process_query(prompt)
        return speech

    def process_query(self, query: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Processes a voice transcript or text query.
        Returns (spoken_reply, tool_result_dict).
        """
        clean_q = query.strip()
        if not clean_q:
            return "I am listening, Sir.", None

        # Layer 1: Fast-Path Heuristic Parser (< 5ms response time)
        fast_result = self._fast_path_parse(clean_q)
        if fast_result is not None:
            speech, tool_res = fast_result
            return speech, tool_res

        # Layer 2: Local LLM Inference (if model loaded)
        if self.llm is not None:
            return self._llm_inference(clean_q)

        # Layer 3: Fallback Conversational Responses
        return self._conversational_fallback(clean_q), None

    def _fast_path_parse(self, query: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """High-speed pattern matcher for instant desktop commands (< 5ms)."""
        q = query.lower().strip()

        # Clean punctuation
        q_clean = re.sub(r"[^\w\s]", " ", q).strip()
        # Strip wake-word prefixes or pleasantries if passed directly:
        q_clean = re.sub(r"^(?:hey\s+nexus|nexus|hey\s+nexas|nexas|hey\s+nexis|nexis)\s*", "", q_clean).strip()
        q_clean = re.sub(r"^(?:please|can\s+you|could\s+you|would\s+you|kindly)\s*", "", q_clean).strip()
        
        # Use stripped query if non-empty, otherwise use raw query
        cmd = q_clean if q_clean else q

        # Conversational Fast Path (< 1ms)
        if cmd in ["who are you", "what is your name", "introduce yourself", "tell me about yourself"]:
            return (
                "I am Nexus, your multimodal AI assistant running natively on Windows and connected to your iQOO 15 phone. "
                "I am standing by to automate your desktop and assist with your workflow.",
                {"status": "success", "action": "introduce"}
            )
        if cmd in ["what can you do", "help", "capabilities", "what are your features"]:
            return (
                "I can open applications like Chrome and VS Code, check system hardware telemetry, take screenshots, "
                "control audio, and sync clipboards directly with your iQOO 15 smartphone.",
                {"status": "success", "action": "help"}
            )
        if cmd in ["hello", "hi", "hey", "greetings", "good morning", "good evening", "good afternoon"]:
            return "Greetings, Sir. All systems are operational. What can I do for you?", {"status": "success", "action": "greeting"}
        if cmd in ["thank you", "thanks", "thank you nexus", "thanks nexus"]:
            return "You are most welcome, Sir. Always at your service.", {"status": "success", "action": "acknowledgement"}

        # Visual Pointing Intent (Clicky Screen Companion - Workflow #2)
        if any(w in cmd for w in ["where is", "point at", "point to", "find the", "show me where", "show me the"]):
            res = JarvisTools.point_at_target(cmd)
            lbl = res.get("label", "the item")
            return f"Pointing at {lbl} on your screen, Sir.", res

        # Multi-Persona Switch Intent (Workflow #16)
        if any(w in cmd for w in ["switch to coder", "activate coder", "become coder"]):
            res = JarvisTools.switch_persona("coder")
            return "Switched to Coder persona. Ready for software engineering, terminal execution, and debugging.", res
        if any(w in cmd for w in ["switch to researcher", "activate researcher", "become researcher"]):
            res = JarvisTools.switch_persona("researcher")
            return "Switched to Researcher persona. Standing by for deep document analysis and data synthesis.", res
        if any(w in cmd for w in ["switch to teacher", "activate teacher", "become teacher"]):
            res = JarvisTools.switch_persona("teacher")
            return "Switched to Teacher persona. Ready to visually guide you through any screen workflow.", res
        if any(w in cmd for w in ["switch to nexus", "activate nexus", "become nexus", "default persona"]):
            res = JarvisTools.switch_persona("nexus")
            return "Executive Nexus persona active, Sir. Desktop automation and telemetry at your command.", res

        # Personal Notes & Knowledge Vault Intent (Workflow #14)
        note_match = re.search(r"^(?:take\s+(?:a\s+)?note|save\s+(?:a\s+)?note|note\s+that)\s*[:\s]\s*(.*)$", cmd)
        if note_match:
            note_body = note_match.group(1).strip()
            if note_body:
                res = JarvisTools.save_note(content=note_body, title=note_body[:30], category="general")
                return f"Saved note to your knowledge vault: '{note_body[:40]}...'", res

        # Type for Me Intent (Workflow #4)
        type_match = re.search(r"^(?:type\s+(?:for\s+me\s+)?|enter\s+(?:text\s+)?|write\s+(?:out\s+)?)\s*[:\s]\s*(.*)$", cmd)
        if type_match:
            text_to_type = type_match.group(1).strip()
            if text_to_type:
                res = JarvisTools.type_text(text_to_type)
                return "Text entered into active window, Sir.", res

        # 0. Direct App & System Trigger Keywords
        DIRECT_APPS = {
            "chrome": ("chrome", "Launching Google Chrome, Sir."),
            "google chrome": ("chrome", "Launching Google Chrome, Sir."),
            "browser": ("chrome", "Launching Google Chrome, Sir."),
            "notepad": ("notepad", "Opening Notepad, Sir."),
            "notes": ("notepad", "Opening Notepad, Sir."),
            "calc": ("calc", "Opening Calculator, Sir."),
            "calculator": ("calc", "Opening Calculator, Sir."),
            "code": ("code", "Opening Visual Studio Code, Sir."),
            "vscode": ("code", "Opening Visual Studio Code, Sir."),
            "vs code": ("code", "Opening Visual Studio Code, Sir."),
            "terminal": ("terminal", "Opening PowerShell terminal, Sir."),
            "cmd": ("terminal", "Opening Command Prompt, Sir."),
            "powershell": ("terminal", "Opening PowerShell, Sir."),
            "settings": ("settings", "Opening Windows Settings, Sir."),
            "spotify": ("spotify", "Opening Spotify, Sir."),
            "paint": ("paint", "Opening Paint, Sir."),
            "taskmgr": ("taskmgr", "Opening Task Manager, Sir."),
            "task manager": ("taskmgr", "Opening Task Manager, Sir."),
            "explorer": ("explorer", "Opening File Explorer, Sir."),
            "files": ("explorer", "Opening File Explorer, Sir."),
        }
        if cmd in DIRECT_APPS:
            app, reply = DIRECT_APPS[cmd]
            return reply, JarvisTools.launch_app(app)

        # 1. App Launching with prefixes (open/launch/start)
        app_patterns = [
            (r"(?:open|launch|start)\s+(?:google\s+)?chrome", "chrome", "Launching Google Chrome, Sir."),
            (r"(?:open|launch|start)\s+(?:the\s+)?browser", "chrome", "Launching Google Chrome, Sir."),
            (r"(?:open|launch|start)\s+(?:notepad|notes|text editor)", "notepad", "Opening Notepad, Sir."),
            (r"(?:open|launch|start)\s+(?:calculator|calc)", "calc", "Opening Calculator."),
            (r"(?:open|launch|start)\s+(?:vscode|code|vs\s*code)", "code", "Launching Visual Studio Code."),
            (r"(?:open|launch|start)\s+(?:terminal|cmd|command prompt|powershell)", "terminal", "Opening PowerShell terminal."),
            (r"(?:open|launch|start)\s+(?:settings|windows settings)", "settings", "Opening Windows Settings."),
            (r"(?:open|launch|start)\s+(?:spotify|music)", "spotify", "Launching Spotify."),
            (r"(?:open|launch|start)\s+(?:explorer|files|file manager)", "explorer", "Opening File Explorer."),
            (r"(?:open|launch|start)\s+(?:task manager|taskmgr)", "taskmgr", "Opening Task Manager."),
            (r"(?:open|launch|start)\s+(?:paint|mspaint)", "paint", "Opening Microsoft Paint."),
        ]
        for pattern, app, reply in app_patterns:
            if re.search(pattern, cmd):
                res = JarvisTools.launch_app(app)
                return reply, res

        # 2. System Telemetry / Hardware Status
        if any(w in cmd for w in ["system status", "hardware status", "cpu usage", "ram usage", "battery", "pc stats", "status", "specs", "cpu"]):
            status_res = JarvisTools.get_system_status()
            if status_res["status"] == "success":
                d = status_res["data"]
                speech = (
                    f"System is operational. CPU load is at {d['cpu']['percent']} percent. "
                    f"RAM usage is {d['memory']['percent']} percent with {d['disk']['free_gb']} gigabytes free on drive C. "
                    f"Battery is at {d['battery']['percent']} percent."
                )
                return speech, status_res
            return "Unable to read system telemetry at this time.", status_res

        # 3. Screenshot Capture
        if any(w in cmd for w in ["take a screenshot", "screenshot the screen", "capture display", "snap screen", "screenshot", "snap"]):
            shot_res = JarvisTools.take_screenshot()
            if shot_res["status"] == "success":
                return "Screen captured and saved to the screenshots repository.", shot_res
            return "Screen capture triggered.", shot_res

        # 4. Media & Volume Control
        if any(w in cmd for w in ["volume up", "increase volume", "louder"]):
            res = JarvisTools.media_control("up")
            return "Increasing system volume.", res
        if any(w in cmd for w in ["volume down", "lower volume", "quieter"]):
            res = JarvisTools.media_control("down")
            return "Decreasing system volume.", res
        if any(w in cmd for w in ["mute audio", "unmute audio", "toggle mute", "mute"]):
            res = JarvisTools.media_control("mute")
            return "Audio mute toggled.", res

        # 5. Office Kit Phone Bridge Actions
        if any(w in cmd for w in ["sync clipboard", "clipboard to phone", "send clipboard to phone"]):
            res = JarvisTools.office_kit_sync_clipboard()
            return "Clipboard synchronized with your iQOO 15 via Vivo Office Kit.", res

        if "send to phone" in cmd or "push to phone" in cmd:
            content = cmd.replace("send to phone", "").replace("push to phone", "").strip()
            res = JarvisTools.office_kit_push_to_phone("NOTIFICATION", {"message": content or "Pushed from Laptop Jarvis"})
            return f"Pushed notification to your iQOO 15.", res

        # 6. Web Search
        search_match = re.search(r"(?:search for|search|google)\s+(.+)", cmd)
        if search_match:
            search_term = search_match.group(1).strip()
            res = JarvisTools.web_search(search_term)
            return f"Searching the web for {search_term}.", res

        return None

    def _llm_inference(self, query: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Executes LLM reasoning using llama_cpp Qwen2.5-0.5B."""
        try:
            # Inject active persona & two-tier persistent memory (Workflows #13 & #16)
            sys_prompt = self.SYSTEM_PROMPT
            try:
                from nexus_personas import personas
                from nexus_memory import memory
                active_p = personas.get_active()
                mem_ctx = memory.get_prompt_context()
                sys_prompt = f"{active_p.system_prompt}\n{self.SYSTEM_PROMPT}\nPersistent Memory: {mem_ctx}"
            except Exception:
                pass

            prompt = (
                f"<|im_start|>system\n{sys_prompt}<|im_end|>\n"
                f"<|im_start|>user\n{query}<|im_end|>\n"
                f"<|im_start|>assistant\n"
            )
            output = self.llm(
                prompt,
                max_tokens=150,
                temperature=0.3,
                stop=["<|im_end|>", "User:"]
            )
            raw_text = output["choices"][0]["text"].strip()
            logger.info(f"LLM Raw Output: {raw_text}")

            # Robust outermost JSON object extraction (handles arbitrary nested brackets)
            start = raw_text.find('{')
            end = raw_text.rfind('}')
            if start != -1 and end != -1 and end > start:
                json_str = raw_text[start:end+1]
                try:
                    payload = json.loads(json_str)
                    tool_name = payload.get("tool")
                    args = payload.get("args", {})
                    speech = payload.get("speech", "Executing your command, Sir.")

                    # Execute tool
                    tool_result = self._dispatch_tool(tool_name, args)
                    return speech, tool_result
                except Exception as je:
                    logger.warning(f"Failed to parse LLM JSON: {je}")

            return raw_text, None

        except Exception as e:
            logger.error(f"LLM inference error: {e}")
            return "My neural cognitive processor encountered an anomaly, Sir.", None

    def _dispatch_tool(self, tool_name: str, args: dict) -> dict:
        """Dispatches dynamic tool call from LLM."""
        if tool_name == "launch_app":
            return JarvisTools.launch_app(args.get("app_name", "notepad"))
        elif tool_name == "system_status":
            return JarvisTools.get_system_status()
        elif tool_name == "take_screenshot":
            return JarvisTools.take_screenshot()
        elif tool_name == "web_search":
            return JarvisTools.web_search(args.get("query", ""))
        elif tool_name == "open_url":
            return JarvisTools.open_url(args.get("url", ""))
        elif tool_name == "media_control":
            return JarvisTools.media_control(args.get("action", "up"))
        elif tool_name == "office_kit_sync":
            return JarvisTools.office_kit_sync_clipboard(args.get("content"))
        elif tool_name == "push_to_phone":
            return JarvisTools.office_kit_push_to_phone(args.get("action", "MESSAGE"), args.get("payload", {}))
        return {"status": "error", "message": f"Unknown tool: {tool_name}"}

    def _conversational_fallback(self, query: str) -> str:
        """Graceful conversational fallback responses."""
        q = query.lower()
        if any(w in q for w in ["hello", "hi nexus", "hey nexus", "greetings"]):
            return "Good day, Sir. All systems are operational. How can I assist you?"
        if any(w in q for w in ["who are you", "what is your name", "introduce yourself"]):
            return (
                "I am Nexus, your elite real-time multimodal AI assistant. "
                "I manage your laptop automation and coordinate with your iQOO 15 phone via Vivo Office Kit."
            )
        if any(w in q for w in ["what can you do", "help", "capabilities"]):
            return (
                "I can open applications, report system telemetry, take screenshots, search the web, "
                "and synchronize tasks or clipboard data directly with your iQOO 15 phone."
            )
        return f"Understood, Sir. Processing your request: {query}."
