"""End-to-End CRUD operations tests (GET, POST, PUT, DELETE) for REST endpoints."""

import pytest
from client.api_client import APIClient
from schemas.models import TaskItemSchema, PaginatedTasksSchema


@pytest.mark.crud
class TestCRUDEndpoints:
    """Validates complete resource lifecycle and HTTP status codes."""

    @pytest.mark.smoke
    def test_healthcheck_endpoint_returns_200(self, api_client: APIClient) -> None:
        response = api_client.health_check()
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    @pytest.mark.smoke
    def test_get_tasks_list_returns_paginated_collection(
        self, auth_qa_client: APIClient
    ) -> None:
        response = auth_qa_client.list_tasks(page=1, per_page=10)
        assert response.status_code == 200
        paginated = PaginatedTasksSchema.model_validate(response.json())
        assert paginated.total == 2
        assert len(paginated.items) == 2

    def test_get_single_task_by_id_returns_200(
        self, auth_qa_client: APIClient
    ) -> None:
        response = auth_qa_client.get_task(1)
        assert response.status_code == 200
        task = TaskItemSchema.model_validate(response.json())
        assert task.id == 1
        assert task.codec == "prores_422"

    def test_get_non_existent_task_returns_404(
        self, auth_qa_client: APIClient
    ) -> None:
        response = auth_qa_client.get_task(9999)
        assert response.status_code == 404
        assert response.json()["error_code"] == "TASK_NOT_FOUND"

    @pytest.mark.smoke
    def test_create_new_task_returns_201_and_persists_resource(
        self, auth_qa_client: APIClient
    ) -> None:
        payload = {
            "title": "Transcode VFX Sequence EXR to ProRes",
            "codec": "openexr",
            "priority": 9,
        }
        create_resp = auth_qa_client.create_task(payload)
        assert create_resp.status_code == 201
        created = TaskItemSchema.model_validate(create_resp.json())
        assert created.title == payload["title"]
        assert created.owner == "david_sdet"

        # Verify persistence via GET
        get_resp = auth_qa_client.get_task(created.id)
        assert get_resp.status_code == 200
        assert get_resp.json()["title"] == payload["title"]

    def test_update_existing_task_returns_200_and_modifies_fields(
        self, auth_qa_client: APIClient
    ) -> None:
        update_payload = {
            "title": "Updated Render Shot 010 Final",
            "codec": "vp9",
            "priority": 10,
            "status": "processing",
        }
        resp = auth_qa_client.update_task(1, update_payload)
        assert resp.status_code == 200
        updated = TaskItemSchema.model_validate(resp.json())
        assert updated.title == "Updated Render Shot 010 Final"
        assert updated.codec == "vp9"
        assert updated.priority == 10
        assert updated.status == "processing"

    def test_update_non_existent_task_returns_404(
        self, auth_qa_client: APIClient
    ) -> None:
        resp = auth_qa_client.update_task(
            8888, {"title": "Ghost Task", "codec": "h264", "priority": 3}
        )
        assert resp.status_code == 404

    def test_admin_delete_task_returns_204_and_removes_resource(
        self, auth_admin_client: APIClient
    ) -> None:
        del_resp = auth_admin_client.delete_task(2)
        assert del_resp.status_code == 204
        assert del_resp.text == ""

        # Subsequent GET and DELETE should return 404 (idempotency verification)
        assert auth_admin_client.get_task(2).status_code == 404
        assert auth_admin_client.delete_task(2).status_code == 404

