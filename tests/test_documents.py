from io import BytesIO

from docx import Document
from fastapi.testclient import TestClient

from analytics_copilot.app import app


def _build_pdf_bytes(text: str) -> bytes:
    stream = f"BT /F1 18 Tf 50 100 Td ({text}) Tj ET\n".encode()
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        (
            b"3 0 obj << /Type /Page /Parent 2 0 R "
            b"/Resources << /Font << /F1 4 0 R >> >> "
            b"/MediaBox [0 0 300 144] /Contents 5 0 R >> endobj\n"
        ),
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        b"5 0 obj << /Length " + str(len(stream)).encode() + b" >> stream\n"
        + stream
        + b"endstream endobj\n",
    ]

    pdf = b"%PDF-1.4\n"
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj

    xref_position = len(pdf)
    pdf += f"xref\n0 {len(offsets)}\n".encode()
    pdf += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        pdf += f"{offset:010d} 00000 n \n".encode()
    pdf += (
        f"trailer << /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref_position}\n%%EOF"
    ).encode()
    return pdf


def _build_docx_bytes(text: str) -> bytes:
    document = Document()
    document.add_paragraph(text)
    output = BytesIO()
    document.save(output)
    return output.getvalue()


def test_create_and_get_document() -> None:
    client = TestClient(app)

    create_response = client.post(
        "/documents",
        json={
            "title": "FastAPI docs",
            "content": "FastAPI is a modern Python web framework.",
            "metadata": {
                "source": "fastapi-docs",
                "source_url": "https://fastapi.tiangolo.com/",
                "tags": ["fastapi", "python"],
            },
        },
    )

    assert create_response.status_code == 201
    created_document = create_response.json()
    assert created_document["id"]
    assert created_document["title"] == "FastAPI docs"
    assert created_document["source_type"] == "manual"
    assert created_document["format"] == "plain_text"
    assert created_document["status"] == "created"
    assert created_document["metadata"]["source"] == "fastapi-docs"
    assert created_document["created_at"] == created_document["updated_at"]

    get_response = client.get(f"/documents/{created_document['id']}")

    assert get_response.status_code == 200
    assert get_response.json() == created_document


def test_upload_text_document() -> None:
    client = TestClient(app)

    response = client.post(
        "/documents/upload",
        files={"file": ("notes.txt", b"Plain text upload", "text/plain")},
    )

    assert response.status_code == 201
    document = response.json()
    assert document["title"] == "notes"
    assert document["content"] == "Plain text upload"
    assert document["source_type"] == "file"
    assert document["format"] == "plain_text"
    assert document["metadata"]["source"] == "uploaded-file"
    assert document["metadata"]["filename"] == "notes.txt"
    assert document["metadata"]["content_type"] == "text/plain"
    assert document["metadata"]["tags"] == ["upload"]


def test_upload_markdown_document() -> None:
    client = TestClient(app)

    response = client.post(
        "/documents/upload",
        files={"file": ("guide.md", b"# Guide\n\nMarkdown upload", "text/markdown")},
    )

    assert response.status_code == 201
    document = response.json()
    assert document["title"] == "guide"
    assert document["content"] == "# Guide\n\nMarkdown upload"
    assert document["source_type"] == "file"
    assert document["format"] == "markdown"


def test_upload_markdown_document_with_long_extension() -> None:
    client = TestClient(app)

    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "guide.markdown",
                b"# Guide\n\nMarkdown upload",
                "text/markdown",
            ),
        },
    )

    assert response.status_code == 201
    document = response.json()
    assert document["title"] == "guide"
    assert document["content"] == "# Guide\n\nMarkdown upload"
    assert document["format"] == "markdown"


def test_upload_pdf_document() -> None:
    client = TestClient(app)

    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "paper.pdf",
                _build_pdf_bytes("PDF upload works"),
                "application/pdf",
            ),
        },
    )

    assert response.status_code == 201
    document = response.json()
    assert document["title"] == "paper"
    assert document["content"] == "PDF upload works"
    assert document["source_type"] == "file"
    assert document["format"] == "pdf"


def test_upload_docx_document() -> None:
    client = TestClient(app)

    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "brief.docx",
                _build_docx_bytes("DOCX upload works"),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
        },
    )

    assert response.status_code == 201
    document = response.json()
    assert document["title"] == "brief"
    assert document["content"] == "DOCX upload works"
    assert document["source_type"] == "file"
    assert document["format"] == "docx"


def test_upload_unsupported_document_format_returns_error_response() -> None:
    client = TestClient(app)

    response = client.post(
        "/documents/upload",
        files={"file": ("archive.zip", b"not supported", "application/zip")},
    )

    assert response.status_code == 415
    assert response.json() == {
        "code": "unsupported_document_format",
        "message": "Unsupported document format",
    }


def test_update_document() -> None:
    client = TestClient(app)
    created_document = client.post(
        "/documents",
        json={"title": "Old title", "content": "Old content"},
    ).json()

    response = client.patch(
        f"/documents/{created_document['id']}",
        json={"title": "New title"},
    )

    assert response.status_code == 200
    updated_document = response.json()
    assert updated_document["title"] == "New title"
    assert updated_document["content"] == "Old content"
    assert updated_document["updated_at"] != created_document["updated_at"]


def test_delete_document() -> None:
    client = TestClient(app)
    created_document = client.post(
        "/documents",
        json={"title": "Temporary", "content": "Delete me"},
    ).json()

    delete_response = client.delete(f"/documents/{created_document['id']}")

    assert delete_response.status_code == 204
    assert client.get(f"/documents/{created_document['id']}").status_code == 404


def test_get_missing_document_returns_error_response() -> None:
    client = TestClient(app)

    response = client.get("/documents/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json() == {
        "code": "document_not_found",
        "message": "Document not found",
    }
