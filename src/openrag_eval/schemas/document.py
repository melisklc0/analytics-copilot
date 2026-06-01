from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentStatus(StrEnum):
    CREATED = "created"
    CHUNKED = "chunked"
    INDEXED = "indexed"
    FAILED = "failed"


class DocumentSourceType(StrEnum):
    MANUAL = "manual"
    FILE = "file"
    URL = "url"
    SYNTHETIC = "synthetic"


class DocumentFormat(StrEnum):
    PLAIN_TEXT = "plain_text"
    MARKDOWN = "markdown"
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"


class DocumentMetadata(BaseModel):
    source: str | None = None
    source_url: str | None = None
    filename: str | None = None
    content_type: str | None = None
    language: str = "en"
    tags: list[str] = Field(default_factory=list)


class DocumentCreate(BaseModel):
    title: str
    content: str
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)


class DocumentRead(BaseModel):
    id: UUID
    title: str
    content: str
    source_type: DocumentSourceType
    format: DocumentFormat
    status: DocumentStatus
    metadata: DocumentMetadata
    created_at: datetime
    updated_at: datetime


class DocumentUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    metadata: DocumentMetadata | None = None
