"""
NEXUS & HEYCLICKY UNIFIED PRODUCTION CONTROL HUB
One-command orchestrator for managing, testing, and monitoring the companion.

Usage:
  python nexus_control.py status   # Shows live system health, PID, audio, and routines
  python nexus_control.py test     # Executes the 10-point end-to-end test suite
  python nexus_control.py start    # Launches companion in windowless background
  python nexus_control.py stop     # Stops all companion background processes
  python nexus_control.py restart  # Restarts all companion subsystems
"""

import os
import sys
import time
import json
import psutil
import subprocess
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
PID_FILE = PROJECT_ROOT / "nexus_daemon.pid"
VBS_LAUNCHER = PROJECT_ROOT / "NexusVoiceAssistant.vbs"
PYTHON_EXE = PROJECT_ROOT.parent / "runtime" / "python" / "python.exe"
TEST_SUITE = CURRENT_DIR / "nexus_test_suite.py"


def get_daemon_status():
    """Checks if Nexus daemon and Clicky companion processes are alive."""
    daemon_pid = None
    daemon_alive = False
    clicky_pids = []

    if PID_FILE.exists():
        try:
            with open(PID_FILE, "r") as f:
                daemon_pid = int(f.read().strip())
            if psutil.pid_exists(daemon_pid):
                proc = psutil.Process(daemon_pid)
                if "python" in proc.name().lower():
                    daemon_alive = True
        except Exception:
            pass

    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if "electron" in proc.info["name"].lower():
                clicky_pids.append(proc.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    return {
        "daemon_alive": daemon_alive,
        "daemon_pid": daemon_pid,
        "clicky_alive": len(clicky_pids) > 0,
        "clicky_pids": clicky_pids
    }


def print_status():
    status = get_daemon_status()
    print("=================================================================")
    print(">>> NEXUS & HEYCLICKY WORKSTATION STATUS <<<")
    print("=================================================================")
    print(f"  Nexus Voice Daemon : {'ONLINE (PID ' + str(status['daemon_pid']) + ')' if status['daemon_alive'] else 'OFFLINE'}")
    print(f"  Clicky Notch & HUD : {'ONLINE (' + str(len(status['clicky_pids'])) + ' instances)' if status['clicky_alive'] else 'OFFLINE'}")
    print(f"  Python Runtime     : {PYTHON_EXE}")

    # Check Routines
    routines_file = DATA_DIR / "routines.json"
    if routines_file.exists():
        try:
            with open(routines_file, "r") as f:
                r_data = json.load(f)
            active = sum(1 for r in r_data.values() if not r.get("paused", False))
            print(f"  Persistent Routines: {active} Active / {len(r_data)} Total")
            for rid, r in r_data.items():
                state = "PAUSED" if r.get("paused") else "ACTIVE"
                print(f"    * [{state}] {r.get('name')}: Next run {r.get('next_run')}")
        except Exception:
            pass

    print("=================================================================")


def stop_all():
    print("Stopping Nexus and Clicky background processes...")
    status = get_daemon_status()
    if status["daemon_alive"]:
        try:
            psutil.Process(status["daemon_pid"]).terminate()
            print(f"Terminated daemon PID {status['daemon_pid']}")
        except Exception:
            pass
    if PID_FILE.exists():
        PID_FILE.unlink(missing_ok=True)

    for pid in status["clicky_pids"]:
        try:
            psutil.Process(pid).terminate()
            print(f"Terminated Electron PID {pid}")
        except Exception:
            pass
    print("All companion processes stopped.")


def start_all():
    print("Starting Nexus Voice Companion via windowless launcher...")
    if VBS_LAUNCHER.exists():
        subprocess.run(["wscript.exe", str(VBS_LAUNCHER)])
        time.sleep(2)
        print_status()
    else:
        print(f"Launcher not found at {VBS_LAUNCHER}")


def main():
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else "status"

    if cmd == "status":
        print_status()
    elif cmd == "test":
        subprocess.run([str(PYTHON_EXE), str(TEST_SUITE)])
    elif cmd == "stop":
        stop_all()
    elif cmd == "start":
        start_all()
    elif cmd == "restart":
        stop_all()
        time.sleep(1)
        start_all()
    else:
        print(f"Unknown command: '{cmd}'. Use status, test, start, stop, or restart.")


if __name__ == "__main__":
    main()
