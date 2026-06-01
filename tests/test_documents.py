from fastapi.testclient import TestClient

from openrag_eval.app import app


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
