"""KnowledgeIndexer: scan cad/ docs at startup, build categorized index."""

from __future__ import annotations

from pathlib import Path

from chippilot.config import CAD_DIR
from chippilot.knowledge.categories import CATEGORIES


class KnowledgeIndexer:
    """Scans the cad/ directory and classifies documents into categories."""

    def __init__(self, cad_dir: Path | None = None):
        self.cad_dir = cad_dir or CAD_DIR
        self.index: dict[str, list[dict]] = {cat: [] for cat in CATEGORIES}
        self._build_index()

    def _build_index(self):
        if not self.cad_dir.exists():
            return
        for f in sorted(self.cad_dir.glob("*.md")):
            name = f.stem.lower()
            matched = False
            for cat, info in CATEGORIES.items():
                for kw in info["keywords"]:
                    if kw.lower() in name:
                        self.index[cat].append({
                            "filename": f.name,
                            "path": str(f),
                            "category": cat,
                        })
                        matched = True
                        break
                if matched:
                    break
            if not matched:
                # Default to workflow
                self.index["workflow"].append({
                    "filename": f.name,
                    "path": str(f),
                    "category": "workflow",
                })

    def summary(self) -> str:
        """Return a concise summary for system prompt or /knowledge command."""
        lines = ["Knowledge Base (cad/ documents):"]
        total = 0
        for cat, info in CATEGORIES.items():
            docs = self.index.get(cat, [])
            total += len(docs)
            lines.append(f"  [{cat}] {info['description']} ({len(docs)} docs)")
            for doc in docs[:3]:
                lines.append(f"    - {doc['filename']}")
            if len(docs) > 3:
                lines.append(f"    ... and {len(docs) - 3} more")
        lines.append(f"\nTotal: {total} documents. Use load_knowledge(topic) for details.")
        return "\n".join(lines)

    def get_docs(self, category: str) -> list[dict]:
        return self.index.get(category, [])

    def find_doc(self, name: str) -> dict | None:
        """Find a document by partial filename match."""
        name_lower = name.lower()
        for docs in self.index.values():
            for doc in docs:
                if name_lower in doc["filename"].lower():
                    return doc
        return None
