from __future__ import annotations

from pathlib import Path
from typing import Iterator

from ..core.exceptions import ValidationError
from ..core.logger import get_logger
from ..core.models import SourceFile
from ..core.utils import sha256_file

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".html", ".htm"}
_SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".idea", ".vscode"}


class DocumentLoader:
    def __init__(
        self,
        extensions: set[str] | None = None,
        logger: object | None = None,
    ) -> None:
        self._extensions = extensions or SUPPORTED_EXTENSIONS
        self._logger = logger or get_logger(self.__class__.__name__)

    def iter_files(self, path: str | Path) -> Iterator[Path]:
        root = Path(path)
        if root.is_file():
            yield root
            return
        if not root.exists():
            raise ValidationError(f"Path does not exist: {path}")
        for item in sorted(root.rglob("*")):
            if not item.is_file():
                continue
            if item.suffix.lower() not in self._extensions:
                continue
            if any(part in _SKIP_DIRS for part in item.parts):
                continue
            yield item

    def load(self, path: str | Path) -> list[SourceFile]:
        sources: list[SourceFile] = []
        for item in self.iter_files(path):
            sources.append(
                SourceFile(
                    path=str(item),
                    filename=item.name,
                    extension=item.suffix.lower(),
                    size=item.stat().st_size,
                    sha256=sha256_file(item),
                )
            )
        self._logger.info("Loaded %d source files from %s", len(sources), path)
        return sources
