from __future__ import annotations

from typing import Any


class LegalAIError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(
        self,
        message: str = "An unexpected error occurred.",
        details: Any = None,
        *,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
        if cause is not None:
            self.__cause__ = cause


class ValidationError(LegalAIError):
    status_code = 400
    code = "validation_error"


class IngestionError(LegalAIError):
    status_code = 500
    code = "ingestion_error"


class ParsingError(IngestionError):
    status_code = 400
    code = "parsing_error"


class DocumentNotFoundError(IngestionError):
    status_code = 404
    code = "document_not_found"


class CollectionNotFoundError(LegalAIError):
    status_code = 404
    code = "collection_not_found"


class QdrantUnavailableError(LegalAIError):
    status_code = 503
    code = "qdrant_unavailable"


class EmbeddingError(LegalAIError):
    status_code = 500
    code = "embedding_error"


class RetrievalError(LegalAIError):
    status_code = 500
    code = "retrieval_error"


class DuplicateDocumentError(LegalAIError):
    status_code = 409
    code = "duplicate_document"
