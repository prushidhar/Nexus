"""
NEXUS TERMINAL-SAFE DICTATION & SCREEN-AWARE WRITING ENGINE
Provides real-time hands-free speech-to-text typing directly into active applications,
with terminal newline sanitization to prevent accidental command execution in shells,
smart punctuation expansion, and screen-aware drafting.
"""

import os
import re
import sys
import time
import ctypes
import logging
import threading
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import pyautogui
import pyperclip
import psutil

# Safe pyautogui configuration
pyautogui.PAUSE = 0.02
pyautogui.FAILSAFE = True

logger = logging.getLogger("NexusDictation")

TERMINAL_PROCESS_NAMES = {
    "windowsterminal.exe",
    "powershell.exe",
    "cmd.exe",
    "conhost.exe",
    "mintty.exe",
    "bash.exe",
    "wsl.exe",
    "git-bash.exe",
    "alacritty.exe",
    "wezterm-gui.exe",
    "hyper.exe",
}

TERMINAL_WINDOW_CLASSES = {
    "ConsoleWindowClass",
    "CASCADIA_HOSTING_WINDOW_CLASS",  # Windows Terminal
    "mintty",
}


def get_foreground_window_info() -> Tuple[int, str, str, str]:
    """
    Returns (hwnd, process_name, window_title, class_name) for current active foreground window.
    """
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return 0, "", "", ""

    # Get Window Title
    length = user32.GetWindowTextLengthW(hwnd)
    title_buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, title_buf, length + 1)
    title = title_buf.value

    # Get Class Name
    class_buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, class_buf, 256)
    class_name = class_buf.value

    # Get Process Name
    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    process_name = ""
    try:
        proc = psutil.Process(pid.value)
        process_name = proc.name().lower()
    except Exception:
        pass

    return hwnd, process_name, title, class_name


def is_active_window_terminal() -> bool:
    """Checks whether the currently focused window is a command prompt or terminal."""
    _, proc_name, title, class_name = get_foreground_window_info()
    if proc_name in TERMINAL_PROCESS_NAMES:
        return True
    if class_name in TERMINAL_WINDOW_CLASSES:
        return True
    # Heuristics on title bar
    lower_title = title.lower()
    if "powershell" in lower_title or "command prompt" in lower_title or "cmd.exe" in lower_title:
        return True
    return False


def format_smart_punctuation(text: str) -> str:
    """Replaces spoken punctuation words with standard punctuation marks."""
    replacements = [
        (r"\bperiod\b", "."),
        (r"\bfull stop\b", "."),
        (r"\bcomma\b", ","),
        (r"\bquestion mark\b", "?"),
        (r"\bexclamation mark\b", "!"),
        (r"\bexclamation point\b", "!"),
        (r"\bcolon\b", ":"),
        (r"\bsemicolon\b", ";"),
        (r"\bopen quote\b", '"'),
        (r"\bclose quote\b", '"'),
        (r"\bopen bracket\b", "("),
        (r"\bclose bracket\b", ")"),
        (r"\bnew line\b", "\n"),
        (r"\bnewline\b", "\n"),
    ]

    res = text
    for pattern, rep in replacements:
        res = re.sub(pattern, rep, res, flags=re.IGNORECASE)

    # Clean spaces before punctuation
    res = re.sub(r"\s+([.,?!:;])", r"\1", res)

    # Auto-capitalize first character
    if res and len(res) > 0:
        res = res[0].upper() + res[1:]

    return res


def sanitize_for_target(text: str, is_terminal: bool) -> str:
    """
    Sanitizes transcription string.
    CRITICAL: In terminal environments, all newlines are strictly replaced
    with spaces to prevent accidental execution of commands!
    """
    if is_terminal:
        # Strictly collapse newlines to spaces or semicolons
        sanitized = re.sub(r"[\r\n]+", " ", text)
        # Strip trailing spaces
        return sanitized.strip()
    return text


class DictationEngine:
    """Handles real-time typing and drafting into foreground Windows applications."""

    def __init__(self, tts=None, clicky_bridge=None, brain=None):
        self.tts = tts
        self.clicky = clicky_bridge
        self.brain = brain
        self.is_dictating = False
        self.lock = threading.Lock()

    def type_text(self, raw_text: str) -> bool:
        """Types formatted text into the active window with terminal safety."""
        if not raw_text or not raw_text.strip():
            return False

        is_term = is_active_window_terminal()
        formatted = format_smart_punctuation(raw_text)
        safe_text = sanitize_for_target(formatted, is_term)

        logger.info(f"Typing into {'Terminal' if is_term else 'Standard Window'}: '{safe_text}'")

        try:
            # Type safely using clipboard + paste for speed and unicode reliability
            old_clipboard = pyperclip.paste()
            pyperclip.copy(safe_text + " ")
            pyautogui.hotkey("ctrl", "v")
            # Restore previous clipboard shortly after
            threading.Timer(0.3, lambda: pyperclip.copy(old_clipboard)).start()
            return True
        except Exception as e:
            logger.error(f"Error typing into active window: {e}")
            return False

    def draft_screen_aware(self, prompt: str) -> str:
        """
        Drafts a response or email using current active window context and local LLM.
        """
        hwnd, proc_name, title, _ = get_foreground_window_info()
        logger.info(f"Screen-aware drafting for window: '{title}' ({proc_name})")

        if self.clicky:
            self.clicky.set_stage("capturing", "Reading window context...")

        system_context = f"The user is focused on application '{proc_name}', window title '{title}'. Draft a concise, high-quality, professional response matching the user's request."
        full_query = f"{system_context}\nUser request: {prompt}\nDraft:"

        draft = ""
        if self.brain:
            draft = self.brain.think(full_query)
        else:
            draft = f"Regarding {title}: {prompt}"

        # Clean draft
        draft = draft.strip()
        if self.clicky:
            self.clicky.set_stage("done", "")

        # Copy to clipboard and type
        pyperclip.copy(draft)
        self.type_text(draft)

        if self.tts:
            self.tts.speak("Draft completed and inserted into your active window.")

        return draft


dictation = DictationEngine()
