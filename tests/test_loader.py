from __future__ import annotations

from app.ingestion.loader import DocumentLoader


def test_loader_recursive(tmp_path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4 x")
    (tmp_path / "sub" / "b.txt").write_text("hello")
    (tmp_path / "c.docx").write_bytes(b"PK")
    (tmp_path / "skip.py").write_text("print(1)")
    sources = DocumentLoader().load(tmp_path)
    names = sorted(source.filename for source in sources)
    assert names == ["a.pdf", "b.txt", "c.docx"]
    assert all(source.sha256 for source in sources)


def test_loader_single_file(tmp_path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("text")
    sources = DocumentLoader().load(path)
    assert len(sources) == 1
    assert sources[0].filename == "note.txt"
