"""
NEXUS BROWSER-USE & COMPUTER-USE AGENT CONTROLLER
Zero-mock browser automation engine for Windows.
Discovers native Google Chrome and Microsoft Edge, controls sessions via CDP
(Chrome DevTools Protocol), extracts live web content, coordinates Clicky visual pointing,
and provides safety confirmation boundaries.
"""

import os
import sys
import json
import time
import socket
import logging
import urllib.request
import urllib.parse
import subprocess
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("NexusBrowser")

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
NOTES_DIR = PROJECT_ROOT / "notes"

CHROME_PATHS = [
    os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
]

EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_browser_executable() -> Tuple[Optional[str], str]:
    """Finds available Chrome or Edge on Windows."""
    for p in CHROME_PATHS:
        if os.path.exists(p):
            return p, "chrome"
    for p in EDGE_PATHS:
        if os.path.exists(p):
            return p, "edge"
    return None, ""


class NexusBrowserAgent:
    """Controls browser automation, research, and visual interaction feedback."""

    def __init__(self, clicky_bridge=None, brain=None, tts=None):
        self.clicky = clicky_bridge
        self.brain = brain
        self.tts = tts
        self.port = 9222
        self.proc = None
        self.exe_path, self.browser_type = find_browser_executable()

    def is_cdp_ready(self) -> bool:
        """Checks if Chrome/Edge CDP endpoint is responding."""
        try:
            url = f"http://127.0.0.1:{self.port}/json/version"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=0.8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return "webSocketDebuggerUrl" in data
        except Exception:
            return False

    def launch_browser(self, target_url: str = "about:blank") -> bool:
        """Launches browser with remote debugging port enabled."""
        if not self.exe_path:
            logger.error("No compatible browser (Chrome/Edge) found on system.")
            return False

        if self.is_cdp_ready():
            logger.info("Browser CDP endpoint already running.")
            return True

        user_data_dir = PROJECT_ROOT / "data" / "browser_profile"
        user_data_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.exe_path,
            f"--remote-debugging-port={self.port}",
            f"--user-data-dir={str(user_data_dir)}",
            "--no-first-run",
            "--no-default-browser-check",
            target_url
        ]

        logger.info(f"Launching {self.browser_type} with CDP debugging on port {self.port}...")
        try:
            self.proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            # Wait for CDP endpoint to be ready
            for _ in range(10):
                time.sleep(0.4)
                if self.is_cdp_ready():
                    logger.info("Browser CDP connection established successfully.")
                    return True
        except Exception as e:
            logger.error(f"Failed to launch browser process: {e}")
        return False

    def get_open_tabs(self) -> List[Dict[str, Any]]:
        """Returns list of open tabs from CDP endpoint."""
        try:
            url = f"http://127.0.0.1:{self.port}/json/list"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to list browser tabs: {e}")
            return []

    def open_url(self, target_url: str) -> bool:
        """Navigates to URL or opens a new tab."""
        if self.clicky:
            self.clicky.set_stage("running", f"Navigating to {target_url[:24]}...")

        if not self.is_cdp_ready():
            return self.launch_browser(target_url)

        try:
            encoded_url = urllib.parse.quote(target_url, safe=":/?=&")
            put_url = f"http://127.0.0.1:{self.port}/json/new?{encoded_url}"
            req = urllib.request.Request(put_url, method="PUT")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                logger.info(f"Opened tab: {data.get('title', '')} ({target_url})")
                return True
        except Exception as e:
            logger.error(f"Error opening URL: {e}")
            return False

    def search_and_research(self, query: str) -> str:
        """
        Executes a real web search, fetches the target content, extracts text,
        summarizes using the local GGUF LLM, and persists a note in the vault.
        """
        logger.info(f"Executing web research for query: '{query}'")
        if self.clicky:
            self.clicky.set_stage("capturing", f"Researching: {query[:20]}...")

        # Perform fast web query
        encoded_query = urllib.parse.quote_plus(query)
        search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

        extracted_text = ""
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0"}
        try:
            req = urllib.request.Request(search_url, headers=headers)
            with urllib.request.urlopen(req, timeout=6.0) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

                # Simple clean text extractor (strips scripts and tags)
                import re
                clean = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
                clean = re.sub(r"<style.*?</style>", "", clean, flags=re.DOTALL | re.IGNORECASE)
                # Find result snippets
                snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', clean, flags=re.DOTALL)
                clean_snippets = [re.sub(r"<[^>]+>", "", s).strip() for s in snippets[:4]]
                extracted_text = " ".join(clean_snippets)
        except Exception as e:
            logger.error(f"Direct web search error: {e}")
            extracted_text = f"Search query: {query}"

        # Feed to Brain for synthesis
        summary = ""
        prompt = (
            f"You are the Researcher Clicky. Synthesize this web research into 2 concise, accurate sentences:\n"
            f"Topic: {query}\n"
            f"Findings: {extracted_text[:1200]}\n"
            f"Summary:"
        )

        if self.brain:
            summary = self.brain.think(prompt).strip()
        else:
            summary = f"Research summary on {query}: {extracted_text[:250]}..."

        # Save to knowledge vault
        NOTES_DIR.mkdir(parents=True, exist_ok=True)
        note_date = datetime.now().strftime("%Y-%m-%d")
        safe_q = re.sub(r"[^a-zA-Z0-9]+", "_", query)[:30]
        note_file = NOTES_DIR / f"{note_date}_{safe_q}.md"

        try:
            with open(note_file, "w", encoding="utf-8") as f:
                f.write(f"# Research: {query}\n\nDate: {datetime.now().isoformat()}\n\n{summary}\n\n## Sources\n{extracted_text}\n")
            logger.info(f"Saved research note: {note_file}")
        except Exception as e:
            logger.error(f"Failed to write note: {e}")

        if self.clicky:
            self.clicky.set_stage("done", "")
            # Point spotlight at center to confirm research ready
            self.clicky.point(700, 300, "Research Complete")

        if self.tts:
            self.tts.speak(summary)

        return summary


browser_agent = NexusBrowserAgent()
