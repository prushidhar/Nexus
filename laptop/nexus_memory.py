"""
NEXUS TWO-TIER PERSISTENT MEMORY & KNOWLEDGE VAULT ENGINE
Implements HeyClicky Workflows #13 (Persistent Memory) & #14 (Notes/Personal Knowledge).
Maintains long-term user profile, ephemeral project state, and a local markdown knowledge vault.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger("NexusMemory")

BASE_DIR = Path(r"C:\Users\P RUSHIDHAR\.gemini\antigravity\scratch\nexus-agent")
MEMORY_DIR = BASE_DIR / "memory"
NOTES_DIR = BASE_DIR / "notes"

MEMORY_DIR.mkdir(parents=True, exist_ok=True)
NOTES_DIR.mkdir(parents=True, exist_ok=True)

PROFILE_FILE = MEMORY_DIR / "user_profile.json"
PROJECT_FILE = MEMORY_DIR / "project_context.json"


class NexusMemory:
    """Two-tier persistent memory store and personal notes vault."""

    def __init__(self):
        self.profile: Dict[str, Any] = self._load_json(PROFILE_FILE, default={
            "user_name": "Sir",
            "assistant_name": "Nexus",
            "preferred_browser": "chrome",
            "preferred_editor": "vscode",
            "theme": "dark",
            "verbosity": "concise",
            "created_at": datetime.now().isoformat()
        })
        self.project_context: Dict[str, Any] = self._load_json(PROJECT_FILE, default={
            "active_project": "Nexus AI Companion",
            "recent_tasks": [],
            "last_active": datetime.now().isoformat()
        })

    def _load_json(self, path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading {path.name}: {e}")
        return default

    def _save_json(self, path: Path, data: Dict[str, Any]):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving {path.name}: {e}")

    # ==================== PROFILE / PREFERENCES (WORKFLOW 13) ====================

    def set_preference(self, key: str, value: Any) -> dict:
        """Sets a persistent user preference."""
        self.profile[key] = value
        self.profile["updated_at"] = datetime.now().isoformat()
        self._save_json(PROFILE_FILE, self.profile)
        logger.info(f"Memory updated: {key} = {value}")
        return {"status": "success", "key": key, "value": value}

    def get_preference(self, key: str, default: Any = None) -> Any:
        return self.profile.get(key, default)

    def update_project_task(self, task_description: str):
        """Records an active project task in ephemeral memory."""
        tasks = self.project_context.get("recent_tasks", [])
        tasks.append({
            "task": task_description,
            "timestamp": datetime.now().isoformat()
        })
        self.project_context["recent_tasks"] = tasks[-10:]  # Keep last 10
        self.project_context["last_active"] = datetime.now().isoformat()
        self._save_json(PROJECT_FILE, self.project_context)

    # ==================== KNOWLEDGE VAULT / NOTES (WORKFLOW 14) ====================

    def save_note(self, content: str, title: Optional[str] = None, category: str = "general") -> dict:
        """
        Saves a structured markdown note into the personal knowledge vault.
        Categories: ideas, bugs, reference, meeting, general.
        """
        cat_dir = NOTES_DIR / category.lower()
        cat_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        date_header = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        clean_title = title or f"Note_{timestamp}"
        safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in clean_title)[:40].strip()
        filename = f"{timestamp}_{safe_title}.md"
        note_path = cat_dir / filename

        md_content = f"# {clean_title}\n\n- **Date**: {date_header}\n- **Category**: {category.title()}\n\n---\n\n{content}\n"

        try:
            with open(note_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            logger.info(f"Note saved to knowledge vault: {note_path.name}")
            return {
                "status": "success",
                "path": str(note_path),
                "title": clean_title,
                "category": category,
                "message": f"Saved note '{clean_title}' in {category} vault."
            }
        except Exception as e:
            logger.error(f"Failed to save note: {e}")
            return {"status": "error", "message": str(e)}

    def list_recent_notes(self, limit: int = 5) -> List[Dict[str, str]]:
        """Returns the most recently modified notes in the vault."""
        notes = []
        for p in NOTES_DIR.rglob("*.md"):
            try:
                notes.append({
                    "title": p.stem,
                    "category": p.parent.name,
                    "modified": p.stat().st_mtime,
                    "path": str(p)
                })
            except Exception:
                pass
        notes.sort(key=lambda x: x["modified"], reverse=True)
        return notes[:limit]

    def get_prompt_context(self) -> str:
        """Generates dynamic memory context to inject into LLM system prompt."""
        recent_tasks = self.project_context.get("recent_tasks", [])
        last_task = recent_tasks[-1]["task"] if recent_tasks else "None"

        return (
            f"User Profile: Name={self.profile.get('user_name', 'Sir')}, "
            f"Preferred Editor={self.profile.get('preferred_editor', 'vscode')}, "
            f"Active Project={self.project_context.get('active_project', 'Nexus Jarvis')}. "
            f"Recent Context: {last_task}."
        )

    get_combined_context = get_prompt_context


memory = NexusMemory()

