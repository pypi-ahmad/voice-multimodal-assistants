from __future__ import annotations

from voice_study_coach.schemas import KnowledgeDoc
from voice_study_coach.tools.knowledge_base import retrieve


def test_retrieve_top_doc() -> None:
    docs = [
        KnowledgeDoc(source="a.md", title="A", text="rollback threshold 1200 ms"),
        KnowledgeDoc(source="b.md", title="B", text="release train tuesday"),
    ]

    hits = retrieve("When rollback at 1200 ms?", docs, top_k=1)

    assert len(hits) == 1
    assert hits[0].doc.source == "a.md"
