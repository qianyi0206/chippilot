"""KnowledgeLoader: load document content on demand (Layer 2 injection)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chippilot.knowledge.indexer import KnowledgeIndexer


class KnowledgeLoader:
    """Loads full document content when agent needs detailed information."""

    def __init__(self, indexer: "KnowledgeIndexer"):
        self.indexer = indexer

    def load(self, topic: str, doc_name: str = None) -> str:
        """Load knowledge document(s) by topic category or specific doc name."""
        if doc_name:
            doc = self.indexer.find_doc(doc_name)
            if not doc:
                return f"Error: Document matching '{doc_name}' not found."
            return self._read_doc(doc)

        # Load by category
        docs = self.indexer.get_docs(topic)
        if not docs:
            available = [c for c, d in self.indexer.index.items() if d]
            return f"Error: No documents in category '{topic}'. Available: {', '.join(available)}"

        # Return list of docs in category with option to load specific one
        lines = [f"Documents in [{topic}] ({len(docs)} total):"]
        for doc in docs:
            lines.append(f"  - {doc['filename']}")
        lines.append(f"\nTo load a specific document, call load_knowledge with doc_name parameter.")

        # Auto-load first doc if 3 or fewer in category
        if len(docs) <= 3:
            lines.append("\n--- Auto-loading documents ---")
            for doc in docs:
                lines.append(self._read_doc(doc))
        return "\n".join(lines)

    def _read_doc(self, doc: dict) -> str:
        path = Path(doc["path"])
        try:
            content = path.read_text()
            # Truncate very long docs
            if len(content) > 20000:
                content = content[:20000] + "\n\n... (truncated, document too long)"
            return f"<knowledge file=\"{doc['filename']}\" category=\"{doc['category']}\">\n{content}\n</knowledge>"
        except Exception as e:
            return f"Error reading {doc['filename']}: {e}"
