"""Assemble system prompt from config + skills + persona + knowledge index."""

from __future__ import annotations

from typing import TYPE_CHECKING

from chippilot.config import WORKDIR, PROJECT_NAME
from chippilot.prompts.persona import PERSONA

if TYPE_CHECKING:
    from chippilot.core.skills import SkillLoader
    from chippilot.knowledge.indexer import KnowledgeIndexer


def build_system_prompt(
    skill_loader: "SkillLoader | None" = None,
    knowledge_indexer: "KnowledgeIndexer | None" = None,
) -> str:
    parts = [
        f"Project: {PROJECT_NAME} | Workspace: {WORKDIR}",
        "",
        PERSONA,
    ]

    if skill_loader:
        parts.append(f"\nAvailable skills (use load_skill to load details):\n{skill_loader.descriptions()}")

    if knowledge_indexer:
        parts.append(f"\nKnowledge base (use load_knowledge to load docs):\n{knowledge_indexer.summary()}")

    return "\n".join(parts)
