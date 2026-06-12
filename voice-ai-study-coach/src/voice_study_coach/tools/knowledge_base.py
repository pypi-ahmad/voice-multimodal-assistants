"""Knowledge loading and lexical retrieval."""

from __future__ import annotations

from pathlib import Path

from voice_study_coach.schemas import KnowledgeDoc, RetrievedDoc

SUPPORTED_SUFFIXES = {".md", ".txt"}


def _extract_title(path: Path, text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return path.stem.replace("_", " ").title()


def _tokenize(text: str) -> set[str]:
    terms: set[str] = set()
    for token in text.split():
        normalized = token.strip(".,:;!?()[]{}\"'").lower()
        if normalized:
            terms.add(normalized)
    return terms


def load_docs(knowledge_dir: Path) -> list[KnowledgeDoc]:
    """Load markdown/text knowledge documents."""
    docs: list[KnowledgeDoc] = []
    for path in sorted(knowledge_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            continue
        docs.append(
            KnowledgeDoc(
                source=path.relative_to(knowledge_dir).as_posix(),
                title=_extract_title(path, text),
                text=text.strip(),
            )
        )
    return docs


def retrieve(query: str, docs: list[KnowledgeDoc], top_k: int) -> list[RetrievedDoc]:
    """Retrieve top docs by lexical overlap."""
    q_terms = _tokenize(query)
    if not q_terms:
        return []

    scored: list[RetrievedDoc] = []
    for doc in docs:
        d_terms = _tokenize(doc.text)
        overlap = len(q_terms & d_terms)
        score = overlap / max(1, len(q_terms))
        scored.append(RetrievedDoc(doc=doc, score=float(score)))

    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[: min(top_k, len(scored))]
