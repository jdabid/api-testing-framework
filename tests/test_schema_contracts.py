"""Strict JSON Schema Contract validation tests using Pydantic v2."""

import pytest
from pydantic import ValidationError
from client.api_client import APIClient
from schemas.models import (
    TaskItemSchema,
    PaginatedTasksSchema,
    TokenResponseSchema,
    ErrorResponseSchema,
)


@pytest.mark.contract
class TestSchemaContracts:
    """Ensures API responses strictly adhere to documented JSON contracts."""

    def test_login_response_matches_strict_token_contract(
        self, api_client: APIClient
    ) -> None:
        response = api_client.login("admin_qa", "AdminPass123!")
        assert response.headers["Content-Type"] == "application/json"
        validated = TokenResponseSchema.model_validate(response.json())
        assert validated.role == "admin"

    def test_task_collection_matches_strict_paginated_contract(
        self, auth_qa_client: APIClient
    ) -> None:
        response = auth_qa_client.list_tasks()
        validated = PaginatedTasksSchema.model_validate(response.json())
        assert isinstance(validated.items, list)
        for item in validated.items:
            assert isinstance(item, TaskItemSchema)

    def test_error_response_matches_standardized_error_contract(
        self, auth_qa_client: APIClient
    ) -> None:
        response = auth_qa_client.get_task(40404)
        assert response.status_code == 404
        validated_err = ErrorResponseSchema.model_validate(response.json())
        assert validated_err.error_code == "TASK_NOT_FOUND"

    def test_pydantic_contract_rejects_undocumented_extra_fields(self) -> None:
        """Verifies contract validator catches schema drift if backend leaks extra fields."""
        corrupted_payload = {
            "id": 10,
            "title": "Valid Title",
            "codec": "h264",
            "priority": 5,
            "status": "queued",
            "owner": "cristian_sdet",
            "created_at": "2026-10-29T12:00:00Z",
            "leaked_internal_db_password": "secret",
        }
        with pytest.raises(ValidationError):
            TaskItemSchema.model_validate(corrupted_payload)

