from __future__ import annotations

from app.ingestion.dedup import DuplicateDetector


def test_exact_duplicate(tmp_path) -> None:
    detector = DuplicateDetector(store_path=tmp_path / "dedup.json")
    text = "This is a legal text about section 300."
    detector.add(text, "doc-1")
    is_duplicate, existing = detector.is_duplicate(text)
    assert is_duplicate is True
    assert existing == "doc-1"


def test_distinct_documents_not_duplicates(tmp_path) -> None:
    detector = DuplicateDetector(store_path=tmp_path / "dedup.json", threshold=0.85)
    detector.add("Murder is the killing of a human being.", "doc-1")
    is_duplicate, _ = detector.is_duplicate(
        "Contract breach gives rise to a claim for damages and specific performance."
    )
    assert is_duplicate is False


def test_near_duplicate(tmp_path) -> None:
    detector = DuplicateDetector(store_path=tmp_path / "dedup.json", threshold=0.5)
    base = "The punishment for murder is imprisonment for life or death according to the code."
    variant = "The punishment for murder is life imprisonment or death according to the code."
    detector.add(base, "doc-1")
    is_duplicate, existing = detector.is_duplicate(variant)
    assert is_duplicate is True
    assert existing == "doc-1"


def test_persistence(tmp_path) -> None:
    store = tmp_path / "dedup.json"
    detector = DuplicateDetector(store_path=store)
    detector.add("Persisted legal text.", "doc-1")
    detector.save()

    reloaded = DuplicateDetector(store_path=store)
    is_duplicate, existing = reloaded.is_duplicate("Persisted legal text.")
    assert is_duplicate is True
    assert existing == "doc-1"
