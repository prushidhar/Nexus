"""
NEXUS OFFICE KIT BRIDGE
========================
Bidirectional IPC between Nexus Laptop Node and iQOO 15 Android companion.

Transport layers (in priority order):
  1. Vivo Office Kit clipboard sync   — instant, zero-config, auto-detected
  2. Office Kit Free Transfer folder  — file drop (robustness fallback)
  3. bridge/shared_clipboard.json     — local JSON file relay (offline / hackathon demo)
  4. bridge/phone_outbox.json         — phone→laptop event stream

Protocol:
  Phone → Laptop : TaskDescriptor JSON (id, type, instruction, payload)
  Laptop → Phone : TaskResult JSON    (taskId, result, tokenCount, source, completedAt)

Actions handled:
  HANDOFF_REQUEST     — escalate NLP task to RTX 2050 / llama.cpp
  WEB_LOOKUP          — autonomous browser research
  PHONE_BATTERY_LOW   — announce warning on speakers
  PHONE_CONNECTED     — announce connect on speakers, update Notch HUD
  PHONE_DISCONNECTED  — update Notch HUD
  CAPTURE_RESULT      — photo / file arrived from phone camera
  ROUTINE_TRIGGER     — phone triggers a laptop routine
  STATUS_PING         — phone checks if laptop is alive; reply with ACK
"""

import os
import sys
import json
import time
import uuid
import logging
import threading
import datetime
from pathlib import Path
from typing import Optional, Callable, Dict, Any

logger = logging.getLogger("OfficeKit")

# ──────────────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BRIDGE_DIR   = PROJECT_ROOT / "bridge"
BRIDGE_DIR.mkdir(parents=True, exist_ok=True)

PHONE_OUTBOX_FILE  = BRIDGE_DIR / "phone_outbox.json"   # phone → laptop events
PHONE_INBOX_FILE   = BRIDGE_DIR / "phone_inbox.json"    # laptop → phone commands
SHARED_CLIP_FILE   = BRIDGE_DIR / "shared_clipboard.json"

# All known Vivo Office Kit sync directories (varies by installation language)
OFFICE_KIT_DIRS = [
    Path.home() / "Documents" / "VivoOfficeKit",
    Path.home() / "Documents" / "OfficeKit" / "FreeTransfer",
    Path.home() / "Documents" / "OfficeKit",
    Path.home() / "Downloads"  / "OfficeKit",
    Path.home() / "NexusTasks",
    BRIDGE_DIR,                          # local hackathon demo fallback
]

POLL_INTERVAL_SEC = 0.5   # How often to poll clipboard + folders

# ──────────────────────────────────────────────────────────────────────────────
# Windows clipboard helpers (ctypes — no extra deps)
# ──────────────────────────────────────────────────────────────────────────────

def _clipboard_read() -> str:
    """Read current clipboard text content on Windows."""
    try:
        import ctypes
        CF_UNICODETEXT = 13
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        if not user32.OpenClipboard(0):
            return ""
        try:
            h = user32.GetClipboardData(CF_UNICODETEXT)
            if not h:
                return ""
            p = kernel32.GlobalLock(h)
            if not p:
                return ""
            try:
                text = ctypes.wstring_at(p)
            finally:
                kernel32.GlobalUnlock(h)
            return text or ""
        finally:
            user32.CloseClipboard()
    except Exception:
        return ""


def _clipboard_write(text: str) -> bool:
    """Write text to Windows clipboard."""
    try:
        import ctypes
        CF_UNICODETEXT = 13
        GMEM_MOVEABLE  = 0x0002
        user32   = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        encoded = (text + "\0").encode("utf-16-le")
        h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
        if not h:
            return False
        p = kernel32.GlobalLock(h)
        ctypes.memmove(p, encoded, len(encoded))
        kernel32.GlobalUnlock(h)

        if not user32.OpenClipboard(0):
            kernel32.GlobalFree(h)
            return False
        user32.EmptyClipboard()
        user32.SetClipboardData(CF_UNICODETEXT, h)
        user32.CloseClipboard()
        return True
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────────────────────
# TaskDescriptor / TaskResult schema helpers
# ──────────────────────────────────────────────────────────────────────────────

def _is_task_descriptor(text: str) -> Optional[dict]:
    """Return parsed TaskDescriptor dict if text is valid, else None."""
    if not text or not text.strip().startswith("{"):
        return None
    try:
        data = json.loads(text.strip())
        if "id" in data and ("instruction" in data or "payload" in data):
            return data
    except Exception:
        pass
    return None


def _make_task_result(task_id: str, result_text: str,
                      token_count: int = 0, source: str = "laptop_nexus") -> dict:
    return {
        "taskId":      task_id,
        "result":      result_text,
        "tokenCount":  token_count,
        "source":      source,
        "completedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "device":      "NEXUS_LAPTOP_NODE",
    }


def _make_laptop_event(action: str, payload: dict = None) -> dict:
    """Build a laptop→phone event record."""
    return {
        "id":        f"evt_{int(time.time() * 1000)}",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source":    "NEXUS_LAPTOP_NODE",
        "target":    "NEXUS_iQOO15_AGENT",
        "action":    action,
        "payload":   payload or {},
    }


# ──────────────────────────────────────────────────────────────────────────────
# Office Kit Bridge class
# ──────────────────────────────────────────────────────────────────────────────

class OfficeKitBridge:
    """
    Runs as a background daemon thread.
    Calls on_task(task: dict) when a new TaskDescriptor arrives from the phone.
    Calls on_event(event: dict) when a phone event (battery, connect, etc.) arrives.
    """

    def __init__(self,
                 on_task:  Callable[[dict], Optional[str]] = None,
                 on_event: Callable[[dict], None]          = None):
        self._on_task  = on_task
        self._on_event = on_event
        self._processed_ids: set = set()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._phone_connected = False
        self._last_clipboard  = ""
        self._ensure_dirs()

    # ── Public API ─────────────────────────────────────────────────────────────

    def start(self):
        """Start the background poll loop."""
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop, daemon=True, name="OfficeKitBridge"
        )
        self._thread.start()
        logger.info("Office Kit Bridge started — monitoring clipboard + Free Transfer folders.")

    def stop(self):
        self._running = False

    def send_to_phone(self, action: str, payload: dict = None) -> bool:
        """
        Write a laptop→phone command into phone_inbox.json.
        Office Kit syncs this file to the iQOO 15 automatically.
        """
        event = _make_laptop_event(action, payload)
        try:
            existing = []
            if PHONE_INBOX_FILE.exists():
                with open(PHONE_INBOX_FILE, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            existing.append(event)
            # Keep last 50 events only
            existing = existing[-50:]
            with open(PHONE_INBOX_FILE, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2)
            logger.info(f"[→ iQOO 15] Sent action={action}")
            return True
        except Exception as e:
            logger.error(f"Failed to write phone_inbox: {e}")
            return False

    def write_result_to_clipboard(self, result: dict) -> bool:
        """
        Write TaskResult JSON to clipboard.
        Office Kit picks this up and syncs to iQOO 15 automatically.
        """
        text = json.dumps(result, indent=2)
        ok = _clipboard_write(text)
        if ok:
            self._last_clipboard = text
            logger.info(f"[→ Clipboard] TaskResult for {result.get('taskId')} written (Office Kit will sync).")
        return ok

    def write_result_to_file(self, result: dict) -> bool:
        """Also drop result file into Free Transfer folder for redundancy."""
        try:
            out_dir = OFFICE_KIT_DIRS[-2]  # NexusTasks folder
            out_dir.mkdir(parents=True, exist_ok=True)
            fname = out_dir / f"nexus_result_{result['taskId']}.json"
            with open(fname, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            logger.info(f"[→ FreeTransfer] Result written to {fname.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to write result file: {e}")
            return False

    def announce_ack(self, task_id: str) -> bool:
        """Write STATUS_ACK back to phone so it knows the laptop is alive."""
        return self.send_to_phone("STATUS_ACK", {"taskId": task_id, "status": "PROCESSING"})

    # ── Internal poll loop ────────────────────────────────────────────────────

    def _loop(self):
        while self._running:
            try:
                self._poll_clipboard()
                self._poll_free_transfer()
                self._poll_phone_outbox()
            except Exception as e:
                logger.debug(f"OfficeKit poll error: {e}")
            time.sleep(POLL_INTERVAL_SEC)

    def _dispatch_task(self, task: dict):
        """Process a new incoming TaskDescriptor from the phone."""
        task_id = task.get("id", f"auto_{uuid.uuid4().hex[:8]}")
        if task_id in self._processed_ids:
            return
        self._processed_ids.add(task_id)
        # Keep set bounded
        if len(self._processed_ids) > 500:
            self._processed_ids = set(list(self._processed_ids)[-200:])

        logger.info(f"[← iQOO 15] Task received: id={task_id} type={task.get('type','?')} instruction={str(task.get('instruction',''))[:80]}")

        # Acknowledge immediately so phone doesn't timeout
        self.announce_ack(task_id)

        result_text = "[Nexus Laptop] Task received."
        token_count = 0

        if self._on_task:
            try:
                out = self._on_task(task)
                if out:
                    result_text = out
            except Exception as e:
                result_text = f"[Nexus Laptop Error] {e}"

        result = _make_task_result(task_id, result_text, token_count)
        self.write_result_to_clipboard(result)
        self.write_result_to_file(result)

    def _dispatch_event(self, event: dict):
        """Process a phone→laptop event (battery, connect, routine trigger, etc.)"""
        action = event.get("action", "UNKNOWN")
        if self._on_event:
            try:
                self._on_event(event)
            except Exception as e:
                logger.debug(f"Event handler error: {e}")

        # Track connection state
        if action == "PHONE_CONNECTED":
            if not self._phone_connected:
                self._phone_connected = True
                logger.info("[Office Kit] iQOO 15 CONNECTED")
        elif action == "PHONE_DISCONNECTED":
            self._phone_connected = False
            logger.info("[Office Kit] iQOO 15 DISCONNECTED")

    def _poll_clipboard(self):
        """Check Windows clipboard for TaskDescriptor or phone events."""
        current = _clipboard_read()
        if not current or current == self._last_clipboard:
            return
        self._last_clipboard = current

        # Could be a TaskDescriptor
        task = _is_task_descriptor(current)
        if task:
            self._dispatch_task(task)
            return

        # Could be a phone event JSON array
        if current.strip().startswith("["):
            try:
                events = json.loads(current.strip())
                if isinstance(events, list):
                    for ev in events:
                        if isinstance(ev, dict) and "action" in ev:
                            self._dispatch_event(ev)
            except Exception:
                pass

    def _poll_free_transfer(self):
        """Check all Office Kit Free Transfer folders for task files."""
        for d in OFFICE_KIT_DIRS:
            if not d.exists():
                continue
            for task_file in sorted(d.glob("nexus_task_*.json")):
                try:
                    with open(task_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    task = _is_task_descriptor(content)
                    if task:
                        self._dispatch_task(task)
                        task_file.rename(task_file.with_suffix(".processed"))
                except Exception as fe:
                    logger.debug(f"Free Transfer read error {task_file}: {fe}")

    def _poll_phone_outbox(self):
        """Check bridge/phone_outbox.json for events written by the Android app."""
        if not PHONE_OUTBOX_FILE.exists():
            return
        try:
            with open(PHONE_OUTBOX_FILE, "r", encoding="utf-8") as f:
                events = json.load(f)
            if not isinstance(events, list):
                return

            for event in events:
                event_id = event.get("id")
                if not event_id or event_id in self._processed_ids:
                    continue

                action = event.get("action", "")

                # TaskDescriptor disguised as event (some Android implementations do this)
                if action in ("HANDOFF_REQUEST", "WEB_LOOKUP", "LONG_CONTEXT_ANALYSIS"):
                    payload = event.get("payload", {})
                    task = {
                        "id":          event_id,
                        "type":        action,
                        "instruction": payload.get("text", payload.get("instruction", "")),
                        "payload":     payload.get("payload", ""),
                    }
                    self._dispatch_task(task)
                else:
                    self._dispatch_event(event)

        except Exception as e:
            logger.debug(f"phone_outbox read error: {e}")

    def _ensure_dirs(self):
        for d in OFFICE_KIT_DIRS:
            try:
                d.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass


# ──────────────────────────────────────────────────────────────────────────────
# Singleton
# ──────────────────────────────────────────────────────────────────────────────

office_kit = OfficeKitBridge()
