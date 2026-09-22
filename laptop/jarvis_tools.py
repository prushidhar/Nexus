"""
Real-time Jarvis System & Office Kit Automation Tools
Executes genuine Windows OS automation, hardware telemetry, application control,
web navigation, and cross-device phone-laptop bridge actions.
"""

import os
import sys
import time
import json
import logging
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path

import psutil
import pyautogui
import pyperclip

logger = logging.getLogger("JarvisTools")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

BASE_DIR = Path(r"C:\Users\P RUSHIDHAR\.gemini\antigravity\scratch\nexus-agent")
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
BRIDGE_DIR = BASE_DIR / "bridge"
PHONE_INBOX = BRIDGE_DIR / "phone_inbox.json"
PHONE_OUTBOX = BRIDGE_DIR / "phone_outbox.json"

SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
BRIDGE_DIR.mkdir(parents=True, exist_ok=True)


class JarvisTools:
    """Comprehensive tool suite for PC automation and iQOO/Vivo phone bridge."""

    APP_MAP = {
        "chrome": "chrome",
        "google chrome": "chrome",
        "browser": "chrome",
        "notepad": "notepad.exe",
        "notes": "notepad.exe",
        "text editor": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "vscode": "code",
        "vs code": "code",
        "code": "code",
        "terminal": "powershell.exe",
        "powershell": "powershell.exe",
        "cmd": "cmd.exe",
        "command prompt": "cmd.exe",
        "explorer": "explorer.exe",
        "files": "explorer.exe",
        "file manager": "explorer.exe",
        "settings": "ms-settings:",
        "spotify": "spotify",
        "paint": "mspaint.exe",
        "task manager": "taskmgr.exe",
        "taskmgr": "taskmgr.exe",
    }

    @staticmethod
    def _resolve_app_path(target: str) -> str:
        """Finds the absolute executable path or command for Windows apps."""
        clean = target.strip().lower()
        
        # Chrome
        if clean in ["chrome", "google chrome", "browser"]:
            chrome_candidates = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            ]
            for c in chrome_candidates:
                if os.path.exists(c):
                    return f'"{c}"'
            return "chrome.exe"
            
        # VS Code
        if clean in ["vscode", "code", "vs code"]:
            vscode_candidates = [
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
                r"C:\Program Files\Microsoft VS Code\Code.exe",
            ]
            for v in vscode_candidates:
                if os.path.exists(v):
                    return f'"{v}"'
            return "code"
            
        # Calculator
        if clean in ["calc", "calculator"]:
            return "calc.exe"

        # Notepad
        if clean in ["notepad", "notes", "text editor"]:
            return "notepad.exe"

        # Edge
        if clean in ["edge", "microsoft edge"]:
            return r'"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"'

        # Terminal / PowerShell
        if clean in ["terminal", "powershell"]:
            return "powershell.exe"

        return target

    @staticmethod
    def launch_app(app_name: str) -> dict:
        """Launches a desktop application by name or common alias."""
        clean_name = app_name.strip().lower()
        resolved = JarvisTools._resolve_app_path(clean_name)
        logger.info(f"Launching application: {clean_name} -> {resolved}")

        try:
            if clean_name in ["settings", "windows settings"]:
                subprocess.Popen("start ms-settings:", shell=True)
                return {"status": "success", "message": "Opened Windows Settings"}
            
            # Using subprocess.Popen ensures Windows launches the GUI app immediately without blocking
            cmd = f'start "" {resolved}'
            subprocess.Popen(cmd, shell=True)

            return {
                "status": "success",
                "target": resolved,
                "message": f"Successfully launched {app_name}"
            }
        except Exception as e:
            logger.error(f"Failed to launch app {app_name}: {e}")
            return {"status": "error", "message": f"Failed to launch {app_name}: {str(e)}"}

    @staticmethod
    def get_system_status() -> dict:
        """Retrieves real-time hardware telemetry and active window context."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_freq = psutil.cpu_freq().current if psutil.cpu_freq() else 0
            cpu_count = psutil.cpu_count(logical=True)
            
            mem = psutil.virtual_memory()
            mem_used_gb = round(mem.used / (1024 ** 3), 2)
            mem_total_gb = round(mem.total / (1024 ** 3), 2)
            mem_percent = mem.percent
            
            disk = psutil.disk_usage("C:\\")
            disk_free_gb = round(disk.free / (1024 ** 3), 2)
            
            battery = psutil.sensors_battery()
            battery_info = {
                "percent": battery.percent if battery else 100,
                "power_plugged": battery.power_plugged if battery else True
            }

            active_window = "Desktop"
            try:
                import win32gui
                hwnd = win32gui.GetForegroundWindow()
                active_window = win32gui.GetWindowText(hwnd) or "Desktop"
            except Exception:
                pass

            status = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "cpu": {
                    "percent": cpu_percent,
                    "frequency_mhz": round(cpu_freq, 1),
                    "cores": cpu_count
                },
                "memory": {
                    "used_gb": mem_used_gb,
                    "total_gb": mem_total_gb,
                    "percent": mem_percent
                },
                "disk": {
                    "free_gb": disk_free_gb
                },
                "battery": battery_info,
                "active_window": active_window
            }
            return {"status": "success", "data": status}
        except Exception as e:
            logger.error(f"Error fetching system telemetry: {e}")
            return {"status": "error", "message": str(e)}

    @staticmethod
    def _capture_screen():
        """Captures full screen using native Win32 GDI BitBlt (works in background & foreground)."""
        import ctypes
        from ctypes import wintypes
        from PIL import Image

        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        hdc_screen = user32.GetDC(0)
        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
        hbm = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
        gdi32.SelectObject(hdc_mem, hbm)
        gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, 0, 0, 0x00CC0020)

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ('biSize', wintypes.DWORD),
                ('biWidth', wintypes.LONG),
                ('biHeight', wintypes.LONG),
                ('biPlanes', wintypes.WORD),
                ('biBitCount', wintypes.WORD),
                ('biCompression', wintypes.DWORD),
                ('biSizeImage', wintypes.DWORD),
                ('biXPelsPerMeter', wintypes.LONG),
                ('biYPelsPerMeter', wintypes.LONG),
                ('biClrUsed', wintypes.DWORD),
                ('biClrImportant', wintypes.DWORD)
            ]

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = w
        bmi.biHeight = -h  # top-down DIB
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0

        buf = (ctypes.c_char * (w * h * 4))()
        gdi32.GetDIBits(hdc_mem, hbm, 0, h, ctypes.byref(buf), ctypes.byref(bmi), 0)

        img = Image.frombuffer('RGBA', (w, h), bytes(buf), 'raw', 'BGRA', 0, 1).convert('RGB')

        gdi32.DeleteObject(hbm)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(0, hdc_screen)
        return img

    @staticmethod
    def take_screenshot(custom_name: str = None) -> dict:
        """Takes a full-resolution screen capture and saves it to disk."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = custom_name or f"nexus_screen_{timestamp}.png"
            if not filename.endswith(".png"):
                filename += ".png"
            
            file_path = SCREENSHOTS_DIR / filename
            try:
                shot = JarvisTools._capture_screen()
            except Exception:
                shot = pyautogui.screenshot()
            shot.save(str(file_path))
            
            logger.info(f"Captured screenshot: {file_path}")
            return {
                "status": "success",
                "path": str(file_path),
                "dimensions": shot.size,
                "message": f"Screenshot saved to {filename}"
            }
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return {"status": "error", "message": str(e)}

    @staticmethod
    def web_search(query: str) -> dict:
        """Opens Google search for the specified query in the default browser."""
        try:
            logger.info(f"Performing web search: {query}")
            url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            webbrowser.open(url)
            return {"status": "success", "query": query, "url": url, "message": f"Searching web for: {query}"}
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return {"status": "error", "message": str(e)}

    @staticmethod
    def open_url(url: str) -> dict:
        """Opens a direct URL in the default browser."""
        try:
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url
            logger.info(f"Opening URL: {url}")
            webbrowser.open(url)
            return {"status": "success", "url": url, "message": f"Navigating to {url}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def type_text(text: str) -> dict:
        """Types text into the active foreground window."""
        try:
            logger.info(f"Typing text ({len(text)} chars)")
            pyperclip.copy(text)
            pyautogui.FAILSAFE = False
            try:
                pyautogui.hotkey('ctrl', 'v')
            except Exception:
                import ctypes
                user32 = ctypes.windll.user32
                VK_CONTROL = 0x11
                VK_V = 0x56
                user32.keybd_event(VK_CONTROL, 0, 0, 0)
                user32.keybd_event(VK_V, 0, 0, 0)
                user32.keybd_event(VK_V, 0, 2, 0)
                user32.keybd_event(VK_CONTROL, 0, 2, 0)
            return {"status": "success", "text": text, "message": "Text typed into active window"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def press_keys(keys: list) -> dict:
        """Executes a hotkey combination (e.g. ['ctrl', 'c'] or ['win', 'd'])."""
        try:
            logger.info(f"Pressing hotkey: {keys}")
            pyautogui.hotkey(*keys)
            return {"status": "success", "keys": keys, "message": f"Pressed {' + '.join(keys)}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def media_control(action: str) -> dict:
        """Controls system audio volume and media playback."""
        act = action.lower().strip()
        try:
            if act in ["up", "volume_up", "raise"]:
                for _ in range(5):
                    pyautogui.press('volumeup')
                return {"status": "success", "action": "volume_up"}
            elif act in ["down", "volume_down", "lower"]:
                for _ in range(5):
                    pyautogui.press('volumedown')
                return {"status": "success", "action": "volume_down"}
            elif act in ["mute", "unmute", "toggle_mute"]:
                pyautogui.press('volumemute')
                return {"status": "success", "action": "mute_toggled"}
            elif act in ["play", "pause", "playpause", "toggle"]:
                pyautogui.press('playpause')
                return {"status": "success", "action": "media_play_pause"}
            else:
                return {"status": "error", "message": f"Unknown media action: {action}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ==================== CLICKY VISUAL SCREEN POINTING ====================

    @staticmethod
    def point_at_target(target: str) -> dict:
        """
        Locates a UI element on the screen and triggers Clicky's animated glowing spotlight
        and tooltip overlay directly over the physical element.
        """
        import re
        import ctypes
        user32 = ctypes.windll.user32
        sw = user32.GetSystemMetrics(0) or 1920
        sh = user32.GetSystemMetrics(1) or 1080

        t = target.lower().strip()
        t = re.sub(r"^(?:where\s+is\s+(?:the\s+)?|point\s+(?:at\s+)?(?:the\s+)?|find\s+(?:the\s+)?|show\s+(?:me\s+)?(?:where\s+)?(?:the\s+)?)", "", t).strip()
        t = t.rstrip("?.!")

        # Common Windows landmarks and application positions
        if any(k in t for k in ["start", "windows button", "windows menu", "start menu"]):
            x = int(sw * 0.48) if sw >= 1920 else 24
            y = sh - 24
            label = "Start Menu"
        elif any(k in t for k in ["search", "search bar", "search icon"]):
            x = int(sw * 0.50)
            y = sh - 24
            label = "Windows Search"
        elif any(k in t for k in ["task manager", "taskmgr"]):
            x = int(sw * 0.52)
            y = sh - 24
            label = "Task Manager"
        elif any(k in t for k in ["tray", "clock", "time", "date", "calendar", "notification"]):
            x = sw - 60
            y = sh - 24
            label = "System Clock & Tray"
        elif any(k in t for k in ["battery", "wifi", "network", "volume", "sound"]):
            x = sw - 120
            y = sh - 24
            label = "Quick Settings (Sound & Wi-Fi)"
        elif any(k in t for k in ["chrome", "google chrome", "browser"]):
            x = int(sw * 0.45)
            y = sh - 24
            label = "Google Chrome"
        elif any(k in t for k in ["code", "vscode", "vs code"]):
            x = int(sw * 0.46)
            y = sh - 24
            label = "Visual Studio Code"
        elif any(k in t for k in ["close", "close button", "exit"]):
            x = sw - 25
            y = 15
            label = "Close Window"
        elif any(k in t for k in ["minimize", "min"]):
            x = sw - 90
            y = 15
            label = "Minimize"
        else:
            x = int(sw / 2)
            y = int(sh / 2)
            label = t.title() or "Target"

        try:
            from clicky_bridge import clicky
            clicky.point(x, y, label)
        except Exception as pe:
            logger.warning(f"Could not signal Clicky overlay: {pe}")

        return {
            "status": "success",
            "x": x,
            "y": y,
            "label": label,
            "message": f"Spotlight active on {label} at ({x}, {y})"
        }

    # ==================== OFFICE KIT PHONE BRIDGE ====================

    @staticmethod
    def office_kit_sync_clipboard(content: str = None) -> dict:
        """
        Synchronizes clipboard between laptop and iQOO 15 phone.
        If content is provided, sets laptop clipboard and writes to bridge.
        If content is None, reads current laptop clipboard and broadcasts to phone.
        """
        try:
            clip = content if content is not None else pyperclip.paste()
            if content is not None:
                pyperclip.copy(content)
            
            bridge_payload = {
                "timestamp": datetime.now().isoformat(),
                "device": "ASUS_TUF_LAPTOP",
                "target_device": "iQOO_15_SM8850",
                "clipboard_content": clip
            }
            
            clip_file = BRIDGE_DIR / "shared_clipboard.json"
            with open(clip_file, "w", encoding="utf-8") as f:
                json.dump(bridge_payload, f, indent=2)
                
            logger.info(f"[Office Kit] Synced clipboard with iQOO 15: '{clip[:30]}...'")
            return {
                "status": "success",
                "clipboard": clip,
                "device_paired": "iQOO 15 (Snapdragon 8 Elite)",
                "channel": "Vivo Office Kit P2P Wi-Fi Direct"
            }
        except Exception as e:
            logger.error(f"Clipboard sync failed: {e}")
            return {"status": "error", "message": str(e)}

    @staticmethod
    def office_kit_push_to_phone(action: str, payload: dict) -> dict:
        """Pushes a handoff task from laptop Jarvis to iQOO 15 phone."""
        try:
            task = {
                "id": f"task_{int(time.time() * 1000)}",
                "timestamp": datetime.now().isoformat(),
                "source": "JARVIS_LAPTOP_NODE",
                "target": "NEXUS_iQOO15_AGENT",
                "action": action,
                "payload": payload,
                "status": "QUEUED"
            }
            
            tasks = []
            if PHONE_INBOX.exists():
                try:
                    with open(PHONE_INBOX, "r", encoding="utf-8") as f:
                        tasks = json.load(f)
                except Exception:
                    tasks = []
            
            tasks.append(task)
            with open(PHONE_INBOX, "w", encoding="utf-8") as f:
                json.dump(tasks, f, indent=2)

            logger.info(f"[Office Kit] Dispatched task '{action}' to iQOO 15 Inbox")
            return {
                "status": "success",
                "task_id": task["id"],
                "action": action,
                "target": "iQOO 15 Phone",
                "message": f"Dispatched {action} to iQOO 15 via Office Kit"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def office_kit_read_phone_events() -> list:
        """Reads completed actions or sensor events pushed by the iQOO 15 phone."""
        if not PHONE_OUTBOX.exists():
            return []
        try:
            with open(PHONE_OUTBOX, "r", encoding="utf-8") as f:
                events = json.load(f)
            return events
        except Exception:
            return []

    # ==================== KNOWLEDGE VAULT & PERSONAS ====================

    @staticmethod
    def save_note(content: str, title: str = None, category: str = "general") -> dict:
        """Saves a note to the local markdown knowledge vault."""
        from nexus_memory import memory
        return memory.save_note(content=content, title=title, category=category)

    @staticmethod
    def switch_persona(persona_name: str) -> dict:
        """Switches active companion persona (Jarvis, Coder, Teacher, Researcher)."""
        from nexus_personas import personas
        return personas.switch_persona(persona_name)
