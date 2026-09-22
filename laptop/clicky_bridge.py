"""
CLICKY WINDOWS VISUAL OVERLAY BRIDGE
Connects Nexus Agent with the Clicky transparent overlay companion.

ROOT CAUSE OF PREVIOUS OOM CRASH:
  ensure_clicky_running() + _ping_ws() was called on EVERY send(), opening
  a new transient WS connection every time while start_listener() kept its own
  persistent connection — 5+ simultaneous WS clients caused V8 heap OOM.

FIX:
  - ensure_clicky_running() called ONCE at startup, stored in _ready flag
  - _send_payload() uses single persistent self._ws; reconnects only on failure
  - start_listener() connects directly without pre-ping; backs off on error
  - NO per-call ensure_clicky_running() / _ping_ws() calls
"""

import os
import sys
import json
import time
import logging
import subprocess
import threading
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from websockets.sync.client import connect as ws_connect
except ImportError:
    ws_connect = None

logger = logging.getLogger("ClickyBridge")

CLICKY_DIR   = Path(r"C:\Users\P RUSHIDHAR\.gemini\antigravity\scratch\repos\clicky-windows")
ELECTRON_EXE = CLICKY_DIR / "node_modules" / "electron" / "dist" / "electron.exe"
MAIN_JS      = CLICKY_DIR / "dist" / "main" / "index.js"
WS_URL       = "ws://127.0.0.1:9876"


class ClickyBridge:
    """Single-connection WebSocket bridge to Clicky overlay. Thread-safe."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._boot()
        return cls._instance

    def _boot(self):
        self._ws:   Optional[object] = None   # persistent send socket
        self._lock  = threading.Lock()
        self._ready = False                   # set once at startup
        self._proc  = None

    # ── Startup ──────────────────────────────────────────────────────────────

    def ensure_clicky_running(self) -> bool:
        """
        Called ONCE at daemon startup.
        Checks if Electron is already running, launches it if not.
        Sets self._ready = True when WS server is reachable.
        """
        if self._ready:
            return True

        if not ELECTRON_EXE.exists() or not MAIN_JS.exists():
            logger.warning(f"Clicky exe not found: {ELECTRON_EXE}")
            return False

        # Already running?
        if self._try_ping():
            self._ready = True
            return True

        # Launch
        try:
            logger.info("Launching Clicky companion overlay...")
            self._proc = subprocess.Popen(
                [str(ELECTRON_EXE), str(MAIN_JS),
                 "--disable-gpu", "--disable-gpu-compositing", "--no-sandbox"],
                cwd=str(CLICKY_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            for _ in range(10):          # wait up to 5s
                time.sleep(0.5)
                if self._try_ping():
                    self._ready = True
                    logger.info("Clicky overlay ready on ws://127.0.0.1:9876")
                    return True
        except Exception as e:
            logger.error(f"Failed to launch Clicky: {e}")
        return False

    def _try_ping(self) -> bool:
        """One-shot lightweight ping — used ONLY during startup."""
        if ws_connect is None:
            return False
        try:
            with ws_connect(WS_URL, open_timeout=0.8, close_timeout=0.3):
                return True
        except Exception:
            return False

    # ── Core send (single persistent socket, reconnect on error) ─────────────

    def _send_payload(self, payload: Dict[str, Any]) -> bool:
        if ws_connect is None or not self._ready:
            return False
        with self._lock:
            # Try existing socket first
            if self._ws is not None:
                try:
                    self._ws.send(json.dumps(payload))
                    return True
                except Exception:
                    try:
                        self._ws.close()
                    except Exception:
                        pass
                    self._ws = None

            # Reconnect once
            try:
                self._ws = ws_connect(WS_URL, open_timeout=1.0)
                self._ws.send(json.dumps(payload))
                return True
            except Exception:
                self._ws = None
                return False

    # ── Public API ───────────────────────────────────────────────────────────

    def point(self, x: int, y: int, label: str, screen: int = 0) -> bool:
        return self._send_payload({
            "action": "point",
            "points": [{"x": int(x), "y": int(y), "label": str(label), "screen": int(screen)}],
        })

    def draw_rect(self, x: int, y: int, w: int, h: int, color: str = "#3b82f6") -> bool:
        return self._send_payload({
            "action": "draw_rect",
            "data": {"x": int(x), "y": int(y), "w": int(w), "h": int(h), "color": str(color)},
        })

    def set_stage(self, stage: str, label: str = "") -> bool:
        return self._send_payload({"action": "stage", "stage": stage, "label": label})

    def show_chat(self) -> bool:
        return self._send_payload({"action": "show_chat"})

    def set_persona(self, persona: str) -> bool:
        return self._send_payload({"action": "set_persona", "persona": persona})

    def set_routine_status(self, summary: str, count: int = 0) -> bool:
        return self._send_payload({"action": "routine_status",
                                   "status": {"summary": summary, "count": count}})

    def expand_notch(self) -> bool:
        return self._send_payload({"action": "expand_notch"})

    def collapse_notch(self) -> bool:
        return self._send_payload({"action": "collapse_notch"})

    def set_phone_status(self, status: str, label: str = "iQOO 15") -> bool:
        """
        Send Office Kit phone status to Notch HUD.
        status: 'connected' | 'disconnected' | 'battery_low' | 'escalating'
        """
        return self._send_payload({"action": "phone_status", "status": status, "label": label})

    def start_listener(self, on_message_callback):
        """
        Single background thread — ONE persistent WebSocket listener.
        Reconnects with exponential backoff. Never spawns extra connections.
        """
        def _listen_loop():
            backoff = 2.0
            while True:
                if not self._ready:
                    time.sleep(1.0)
                    continue
                try:
                    with ws_connect(WS_URL, open_timeout=3.0) as ws:
                        logger.info("Connected to Clicky WebSocket incoming stream.")
                        backoff = 2.0          # reset on successful connect
                        for raw in ws:
                            try:
                                msg = json.loads(raw)
                                on_message_callback(msg)
                            except Exception as me:
                                logger.debug(f"Clicky msg error: {me}")
                except Exception:
                    pass
                time.sleep(backoff)
                backoff = min(backoff * 1.5, 15.0)   # cap at 15s

        t = threading.Thread(target=_listen_loop, daemon=True, name="ClickyWSListener")
        t.start()


clicky = ClickyBridge()
