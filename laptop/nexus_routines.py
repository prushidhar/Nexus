"""
NEXUS PERSISTENT ROUTINE AUTOMATION ENGINE
Provides autonomous scheduled routines, sleeping-machine catchup,
offline network deferral, and 3-consecutive-failure auto-pause protection.
"""

import os
import sys
import json
import time
import socket
import logging
import threading
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
ROUTINES_FILE = DATA_DIR / "routines.json"

logger = logging.getLogger("NexusRoutines")


def is_internet_available(host: str = "8.8.8.8", port: int = 53, timeout: float = 1.5) -> bool:
    """Checks if active internet connection is available."""
    try:
        socket.setdefaulttimeout(timeout)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
        return True
    except (socket.timeout, socket.error):
        return False


class TaskState:
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


class FlowState:
    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PAUSED = "PAUSED"


def task(name: Optional[str] = None, retries: int = 0, retry_delay_seconds: float = 1.0):
    """Prefect-style task decorator with automatic retry and execution tracking."""
    def decorator(func):
        task_name = name or func.__name__

        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts <= retries:
                try:
                    logger.debug(f"[Task: {task_name}] Attempt {attempts + 1} starting...")
                    res = func(*args, **kwargs)
                    logger.debug(f"[Task: {task_name}] Completed successfully.")
                    return res
                except Exception as e:
                    attempts += 1
                    if attempts > retries:
                        logger.error(f"[Task: {task_name}] Failed after {attempts} attempts: {e}")
                        raise
                    logger.warning(f"[Task: {task_name}] Retrying in {retry_delay_seconds}s after: {e}")
                    time.sleep(retry_delay_seconds)

        wrapper.__name__ = task_name
        return wrapper
    return decorator


def flow(name: Optional[str] = None, schedule_hours: Optional[int] = None, allow_catchup: bool = True):
    """Prefect-style flow decorator for orchestrating multi-task pipelines."""
    def decorator(func):
        flow_name = name or func.__name__

        def wrapper(*args, **kwargs):
            logger.info(f"[Flow: {flow_name}] Starting execution...")
            start_time = time.time()
            try:
                res = func(*args, **kwargs)
                dur = time.time() - start_time
                logger.info(f"[Flow: {flow_name}] Completed successfully in {dur:.2f}s")
                return res
            except Exception as e:
                dur = time.time() - start_time
                logger.error(f"[Flow: {flow_name}] Failed in {dur:.2f}s: {e}")
                raise

        wrapper.__name__ = flow_name
        return wrapper
    return decorator


class RoutineEngine:
    """Manages scheduled background automation routines with resilience guarantees."""

    def __init__(self, tts=None, clicky_bridge=None):
        self.tts = tts
        self.clicky = clicky_bridge
        self.lock = threading.Lock()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.last_check_timestamp = time.time()
        self.routines: Dict[str, Dict[str, Any]] = {}
        self.action_registry: Dict[str, Callable[[], str]] = {}

        self._register_default_actions()
        self.load_routines()

    def _register_default_actions(self):
        """Registers built-in real routines."""
        self.action_registry["morning_briefing"] = self._action_morning_briefing
        self.action_registry["git_watch_summary"] = self._action_git_watch_summary
        self.action_registry["cache_hygiene"] = self._action_cache_hygiene

    def _get_default_routines(self) -> Dict[str, Dict[str, Any]]:
        now = datetime.now()
        tomorrow_9am = datetime(now.year, now.month, now.day, 9, 0, 0)
        if tomorrow_9am <= now:
            tomorrow_9am += timedelta(days=1)

        return {
            "morning_briefing": {
                "id": "morning_briefing",
                "name": "Daily Morning Standup Briefing",
                "interval_hours": 24,
                "target_hour": 9,
                "target_minute": 0,
                "action": "morning_briefing",
                "allow_catchup": True,
                "requires_network": True,
                "last_run": None,
                "next_run": tomorrow_9am.isoformat(),
                "failure_count": 0,
                "paused": False,
                "last_error": None
            },
            "git_watch_summary": {
                "id": "git_watch_summary",
                "name": "Repository Changes Watcher",
                "interval_hours": 3,
                "target_hour": None,
                "target_minute": None,
                "action": "git_watch_summary",
                "allow_catchup": False,
                "requires_network": False,
                "last_run": None,
                "next_run": (now + timedelta(hours=3)).isoformat(),
                "failure_count": 0,
                "paused": False,
                "last_error": None
            },
            "cache_hygiene": {
                "id": "cache_hygiene",
                "name": "Workspace Cache & Scratch Cleaner",
                "interval_hours": 168,  # Weekly
                "target_hour": 0,
                "target_minute": 0,
                "action": "cache_hygiene",
                "allow_catchup": True,
                "requires_network": False,
                "last_run": None,
                "next_run": (now + timedelta(days=7)).isoformat(),
                "failure_count": 0,
                "paused": False,
                "last_error": None
            }
        }

    def load_routines(self):
        """Loads routines from disk, creating defaults if missing."""
        with self.lock:
            if ROUTINES_FILE.exists():
                try:
                    with open(ROUTINES_FILE, "r", encoding="utf-8") as f:
                        self.routines = json.load(f)
                    logger.info(f"Loaded {len(self.routines)} routines from {ROUTINES_FILE}")
                    return
                except Exception as e:
                    logger.error(f"Error reading routines.json: {e}")

            self.routines = self._get_default_routines()
            self._save_routines_locked()

    def _save_routines_locked(self):
        """Saves current routines to disk (must hold self.lock)."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(ROUTINES_FILE, "w", encoding="utf-8") as f:
                json.dump(self.routines, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save routines.json: {e}")

    def save_routines(self):
        with self.lock:
            self._save_routines_locked()

    def register_action(self, name: str, func: Callable[[], str]):
        self.action_registry[name] = func

    # --- Built-in Action Implementations (Prefect Flow & Task Architecture) ---

    @task(name="InspectGitRepositories", retries=2, retry_delay_seconds=0.5)
    def _task_git_inspection(self) -> str:
        """Inspects git working directories for modified or uncommitted files."""
        scratch_dir = PROJECT_ROOT.parent
        repos = ["nexus-agent", "repos/clicky-windows", "repos/browser-use"]
        git_updates = []
        for r in repos:
            repo_path = scratch_dir / r
            if (repo_path / ".git").exists():
                try:
                    res = subprocess.run(
                        ["git", "status", "--porcelain"],
                        cwd=str(repo_path),
                        capture_output=True,
                        text=True,
                        timeout=3
                    )
                    changes = len([line for line in res.stdout.splitlines() if line.strip()])
                    if changes > 0:
                        git_updates.append(f"{r}: {changes} uncommitted files")
                except Exception:
                    pass
        return ", ".join(git_updates) if git_updates else "all repositories clean"

    @task(name="InspectSystemTelemetry", retries=1)
    def _task_system_telemetry(self) -> str:
        """Extracts workstation battery, uptime, and CPU usage."""
        import psutil
        now_str = datetime.now().strftime("%A, %B %d, %I:%M %p")
        battery = psutil.sensors_battery()
        bat_str = f"{battery.percent}%" if battery else "Plugged into AC"
        cpu = psutil.cpu_percent(interval=0.5)
        return f"Good morning. It is {now_str}. System battery is at {bat_str}, CPU load is {cpu} percent"

    @flow(name="MorningBriefingFlow")
    def _action_morning_briefing(self) -> str:
        """Prefect-style Morning Briefing Flow orchestrating telemetry and git status."""
        sys_status = self._task_system_telemetry()
        git_summary = self._task_git_inspection()
        report = f"{sys_status}. In your workspace: {git_summary}."
        logger.info(f"Morning Briefing Executed: {report}")
        return report

    @flow(name="GitWatchSummaryFlow")
    def _action_git_watch_summary(self) -> str:
        """Scans active workspace for uncommitted work."""
        git_summary = self._task_git_inspection()
        result = f"Git check completed. Workspace status: {git_summary}."
        logger.info(result)
        return result

    @flow(name="WorkspaceHygieneFlow")
    def _action_cache_hygiene(self) -> str:
        """Cleans empty directories and temp files."""
        scratch_dir = PROJECT_ROOT.parent
        cleaned_count = 0
        bytes_reclaimed = 0

        # Scan for orphaned .tmp files
        for root, dirs, files in os.walk(str(scratch_dir)):
            if ".git" in root or "node_modules" in root:
                continue
            for f in files:
                if f.endswith(".tmp") or f.startswith("tmp_"):
                    p = Path(root) / f
                    try:
                        bytes_reclaimed += p.stat().st_size
                        p.unlink()
                        cleaned_count += 1
                    except Exception:
                        pass

        kb = bytes_reclaimed / 1024
        msg = f"Workspace hygiene routine finished. Cleaned {cleaned_count} temporary files, reclaiming {kb:.1f} KB."
        logger.info(msg)
        return msg

    # --- Execution & Resilience Pipeline ---

    def execute_routine(self, routine_id: str, is_catchup: bool = False) -> bool:
        """Executes a single routine through the 7-stage pipeline."""
        with self.lock:
            routine = self.routines.get(routine_id)
            if not routine:
                logger.warning(f"Routine {routine_id} not found")
                return False

            if routine.get("paused", False):
                logger.info(f"Routine {routine_id} is paused. Skipping.")
                return False

            action_name = routine.get("action")
            action_fn = self.action_registry.get(action_name)
            if not action_fn:
                logger.error(f"No action registered for {action_name}")
                return False

            # Check network requirement
            if routine.get("requires_network", False) and not is_internet_available():
                logger.warning(f"Routine {routine_id} requires network, but offline. Deferring 5 minutes.")
                defer_time = datetime.now() + timedelta(minutes=5)
                routine["next_run"] = defer_time.isoformat()
                self._save_routines_locked()
                if self.clicky:
                    self.clicky.set_routine_status(f"{routine['name']} deferred (offline)")
                return False

        logger.info(f"Triggering routine: {routine_id} (Catchup: {is_catchup})")
        if self.clicky:
            prefix = "Catching up: " if is_catchup else "Running routine: "
            self.clicky.set_stage("running", f"{prefix}{routine['name']}")

        success = False
        result_message = ""
        try:
            result_message = action_fn()
            success = True
        except Exception as e:
            logger.error(f"Routine {routine_id} failed with error: {e}", exc_info=True)
            result_message = f"Error: {str(e)}"

        now = datetime.now()
        with self.lock:
            routine = self.routines.get(routine_id, {})
            routine["last_run"] = now.isoformat()

            if success:
                routine["failure_count"] = 0
                routine["last_error"] = None
                # Calculate next run
                interval_hours = routine.get("interval_hours", 24)
                target_hour = routine.get("target_hour")
                target_minute = routine.get("target_minute", 0)

                if target_hour is not None:
                    next_dt = datetime(now.year, now.month, now.day, target_hour, target_minute, 0)
                    if next_dt <= now:
                        next_dt += timedelta(days=1)
                    routine["next_run"] = next_dt.isoformat()
                else:
                    routine["next_run"] = (now + timedelta(hours=interval_hours)).isoformat()
            else:
                routine["failure_count"] = routine.get("failure_count", 0) + 1
                routine["last_error"] = result_message
                if routine["failure_count"] >= 3:
                    routine["paused"] = True
                    logger.critical(f"Circuit breaker tripped: Auto-paused routine '{routine_id}' after 3 consecutive failures.")
                    if self.tts:
                        self.tts.speak(f"Alert: I have auto-paused the routine {routine['name']} after 3 failures.")

            self._save_routines_locked()

        if self.clicky:
            self.clicky.set_stage("done", "")
            self.clicky.set_routine_status(self.get_status_summary())

        if success and routine.get("id") == "morning_briefing" and self.tts:
            self.tts.speak(result_message)

        return success

    def get_status_summary(self) -> str:
        """Returns concise summary for Notch HUD."""
        with self.lock:
            active_count = sum(1 for r in self.routines.values() if not r.get("paused", False))
            paused_count = len(self.routines) - active_count
            next_routine = None
            next_time = None

            now = datetime.now()
            for r in self.routines.values():
                if r.get("paused", False):
                    continue
                try:
                    nr = datetime.fromisoformat(r["next_run"])
                    if next_time is None or nr < next_time:
                        next_time = nr
                        next_routine = r
                except Exception:
                    pass

            if next_routine and next_time:
                time_str = next_time.strftime("%I:%M %p")
                return f"{next_routine['name'][:18]} @ {time_str}"
            return f"{active_count} active routines"

    # --- Background Loop with Sleeping-Machine Catchup ---

    def start(self):
        """Starts background monitoring thread."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True, name="NexusRoutineScheduler")
        self.thread.start()
        logger.info("Routine automation scheduler thread running.")

    def stop(self):
        self.running = False

    def _scheduler_loop(self):
        self.last_check_timestamp = time.time()

        while self.running:
            try:
                current_time = time.time()
                time_jump = current_time - self.last_check_timestamp

                # Detect sleeping machine / power state resume (gap > 60s)
                is_sleep_resume = time_jump > 60.0
                if is_sleep_resume:
                    logger.info(f"System wake detected (time jumped {time_jump:.1f}s). Checking for missed routines.")

                now = datetime.now()
                routines_to_run = []

                with self.lock:
                    for r_id, r in list(self.routines.items()):
                        if r.get("paused", False):
                            continue
                        try:
                            next_dt = datetime.fromisoformat(r["next_run"])
                            if next_dt <= now:
                                if is_sleep_resume:
                                    if r.get("allow_catchup", True):
                                        routines_to_run.append((r_id, True))
                                    else:
                                        # Advance to next scheduled window without running
                                        r["next_run"] = (now + timedelta(hours=r.get("interval_hours", 24))).isoformat()
                                else:
                                    routines_to_run.append((r_id, False))
                        except Exception as e:
                            logger.error(f"Error checking schedule for {r_id}: {e}")

                for r_id, is_catchup in routines_to_run:
                    self.execute_routine(r_id, is_catchup=is_catchup)

                self.last_check_timestamp = time.time()
                time.sleep(10)

            except Exception as e:
                logger.error(f"Exception in routine scheduler loop: {e}", exc_info=True)
                time.sleep(10)


routines = RoutineEngine()
