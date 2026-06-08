from uuid import UUID

from fastapi import APIRouter, File, UploadFile, status

from analytics_copilot.core.exceptions import DocumentNotFoundError
from analytics_copilot.schemas.document import (
    DocumentCreate,
    DocumentMetadata,
    DocumentRead,
    DocumentUpdate,
)
from analytics_copilot.services.document_extractors import document_extractor_service
from analytics_copilot.services.documents import document_service


router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def create_document(payload: DocumentCreate) -> DocumentRead:
    return await document_service.create_document(payload)


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)) -> DocumentRead:
    data = await file.read()
    parsed_upload = await document_extractor_service.parse_upload(
        filename=file.filename or "",
        data=data,
    )
    metadata = DocumentMetadata(
        source="uploaded-file",
        filename=file.filename,
        content_type=file.content_type,
        tags=["upload"],
    )
    return await document_service.create_file_document(
        title=parsed_upload.title,
        content=parsed_upload.content,
        format=parsed_upload.format,
        metadata=metadata,
    )


@router.get("", response_model=list[DocumentRead])
async def list_documents() -> list[DocumentRead]:
    return await document_service.list_documents()


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(document_id: UUID) -> DocumentRead:
    document = await document_service.get_document(document_id)
    if document is None:
        raise DocumentNotFoundError()
    return document


@router.patch("/{document_id}", response_model=DocumentRead)
async def update_document(document_id: UUID, payload: DocumentUpdate) -> DocumentRead:
    document = await document_service.update_document(document_id, payload)
    if document is None:
        raise DocumentNotFoundError()
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: UUID) -> None:
    deleted = await document_service.delete_document(document_id)
    if not deleted:
        raise DocumentNotFoundError()
