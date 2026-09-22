"""
NEXUS MULTI-PERSONA "CLICKYS" ARCHITECTURE (SEPTEMBER 2026 ENGINE)
Implements HeyClicky Workflow #16 (Named Specialized Clickys).
Provides dynamic switching between specialized companions:
- Nexus (Executive Companion / Desktop Automation)
- Coder (Software Engineering & Terminal Expert)
- Teacher (Visual UI Walkthrough & Screen Guide)
- Researcher (Deep Synthesis & Knowledge Vault Analyst)
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("NexusPersonas")


class Persona:
    def __init__(self, name: str, role: str, system_prompt: str, accent_color: str, tts_rate: int = 175):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.accent_color = accent_color
        self.tts_rate = tts_rate


PERSONAS = {
    "nexus": Persona(
        name="Nexus",
        role="Executive Desktop Companion",
        system_prompt=(
            "You are Nexus, an elite executive AI companion for Windows PC. "
            "You control OS operations, monitor telemetry, and automate workflows with crisp confidence. "
            "Address the user respectfully as Sir. Keep answers under 2 sentences unless elaborating on technical details."
        ),
        accent_color="#3B82F6",  # Electric Blue
        tts_rate=175
    ),
    "coder": Persona(
        name="Coder",
        role="Senior Software Engineer",
        system_prompt=(
            "You are Coder, an expert programming companion. You specialize in Python, TypeScript, Git, "
            "and Windows terminal automation. Give precise, production-grade solutions, code diffs, and exact commands."
        ),
        accent_color="#8B5CF6",  # Purple/Violet
        tts_rate=185
    ),
    "teacher": Persona(
        name="Teacher",
        role="Visual UI Walkthrough Guide",
        system_prompt=(
            "You are Teacher, a patient screen walkthrough guide. When the user asks how to do something, "
            "you explain the step clearly and always emit POINT tags to spotlight the exact button or menu on their screen."
        ),
        accent_color="#10B981",  # Emerald Green
        tts_rate=165
    ),
    "researcher": Persona(
        name="Researcher",
        role="Deep Knowledge Analyst",
        system_prompt=(
            "You are Researcher, an analytical assistant skilled at digesting documents, synthesizing data, "
            "and extracting actionable insights from the web and knowledge vault."
        ),
        accent_color="#F59E0B",  # Amber
        tts_rate=170
    )
}


class PersonaManager:
    """Manages active persona state and routing."""

    def __init__(self):
        self.active_persona: Persona = PERSONAS["nexus"]

    def switch_persona(self, target_name: str) -> dict:
        """Switches the active companion persona."""
        clean = target_name.lower().strip()
        matched = None
        for key, p in PERSONAS.items():
            if key in clean or p.name.lower() in clean:
                matched = p
                break

        if matched:
            self.active_persona = matched
            logger.info(f"Switched persona to: {matched.name} ({matched.role})")
            return {
                "status": "success",
                "name": matched.name,
                "role": matched.role,
                "accent_color": matched.accent_color,
                "message": f"Switched to {matched.name} ({matched.role})"
            }

        return {"status": "error", "message": f"Persona '{target_name}' not found."}

    def get_active(self) -> Persona:
        return self.active_persona

    def list_personas(self) -> list:
        return [{"name": p.name, "role": p.role, "color": p.accent_color} for p in PERSONAS.values()]


personas = PersonaManager()
