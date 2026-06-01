from datetime import UTC, datetime
from uuid import UUID, uuid4

from openrag_eval.schemas.document import (
    DocumentCreate,
    DocumentFormat,
    DocumentMetadata,
    DocumentRead,
    DocumentSourceType,
    DocumentStatus,
    DocumentUpdate,
)


class DocumentService:
    """Manage documents before persistent storage is introduced."""

    def __init__(self) -> None:
        self._documents: dict[UUID, DocumentRead] = {}

    async def create_document(self, payload: DocumentCreate) -> DocumentRead:
        now = datetime.now(UTC)
        document = DocumentRead(
            id=uuid4(),
            title=payload.title,
            content=payload.content,
            source_type=DocumentSourceType.MANUAL,
            format=DocumentFormat.PLAIN_TEXT,
            status=DocumentStatus.CREATED,
            metadata=payload.metadata,
            created_at=now,
            updated_at=now,
        )
        self._documents[document.id] = document
        return document

    async def create_file_document(
        self,
        *,
        title: str,
        content: str,
        format: DocumentFormat,
        metadata: DocumentMetadata,
    ) -> DocumentRead:
        now = datetime.now(UTC)
        document = DocumentRead(
            id=uuid4(),
            title=title,
            content=content,
            source_type=DocumentSourceType.FILE,
            format=format,
            status=DocumentStatus.CREATED,
            metadata=metadata,
            created_at=now,
            updated_at=now,
        )
        self._documents[document.id] = document
        return document

    async def list_documents(self) -> list[DocumentRead]:
        return list(self._documents.values())

    async def get_document(self, document_id: UUID) -> DocumentRead | None:
        return self._documents.get(document_id)

    async def update_document(
        self,
        document_id: UUID,
        payload: DocumentUpdate,
    ) -> DocumentRead | None:
        document = self._documents.get(document_id)
        if document is None:
            return None

        update_data = payload.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now(UTC)
        updated_document = document.model_copy(update=update_data)
        self._documents[document_id] = updated_document
        return updated_document

    async def delete_document(self, document_id: UUID) -> bool:
        return self._documents.pop(document_id, None) is not None


document_service = DocumentService()

# document_service şu anda in-memory singleton:
# Bu yüzden testlerde oluşturulan dokümanlar aynı process içinde kalabilir. 
# Mesela bir test POST /documents yapar, sonra başka bir test GET /documents 
# çağırırsa önceki testten kalan dokümanı görebilir. 
# Bu ileride testleri kırılgan yapabilir.

# TODO
# boş title / boş content validation testi
# testler arası in-memory document_service state sızıyor mu kontrol
