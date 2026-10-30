"""Authentication, JWT token lifecycle, and Role-Based Access Control (RBAC) tests."""

import pytest
from client.api_client import APIClient
from schemas.models import TokenResponseSchema, ErrorResponseSchema


@pytest.mark.auth
class TestJWTAuthentication:
    """Test suite for JWT authentication and RBAC authorization policies."""

    @pytest.mark.smoke
    def test_valid_login_returns_jwt_bearer_token(self, api_client: APIClient) -> None:
        response = api_client.login("david_sdet", "SdetPass123!")
        assert response.status_code == 200

        token_data = TokenResponseSchema.model_validate(response.json())
        assert token_data.token_type == "Bearer"
        assert token_data.role == "qa_engineer"
        assert token_data.access_token.startswith("jwt_")

    @pytest.mark.parametrize(
        "username,password,expected_status,expected_code",
        [
            ("david_sdet", "WrongPassword!", 401, "INVALID_CREDENTIALS"),
            ("non_existent_user", "SdetPass123!", 401, "INVALID_CREDENTIALS"),
            ("", "SdetPass123!", 400, "MISSING_CREDENTIALS"),
            ("david_sdet", "", 400, "MISSING_CREDENTIALS"),
        ],
    )
    def test_invalid_login_attempts_are_rejected(
        self,
        api_client: APIClient,
        username: str,
        password: str,
        expected_status: int,
        expected_code: str,
    ) -> None:
        response = api_client.login(username, password)
        assert response.status_code == expected_status
        err = ErrorResponseSchema.model_validate(response.json())
        assert err.error_code == expected_code

    def test_protected_endpoint_rejects_unauthenticated_request(
        self, api_client: APIClient
    ) -> None:
        response = api_client.list_tasks()
        assert response.status_code == 401
        err = ErrorResponseSchema.model_validate(response.json())
        assert err.error_code == "UNAUTHORIZED"

    def test_protected_endpoint_rejects_tampered_jwt_token(
        self, api_client: APIClient
    ) -> None:
        api_client.set_token("jwt_tampered_invalid_signature_token_999")
        response = api_client.list_tasks()
        assert response.status_code == 401

    def test_viewer_role_cannot_create_or_update_tasks(
        self, auth_viewer_client: APIClient
    ) -> None:
        create_resp = auth_viewer_client.create_task(
            {"title": "Unauthorized Task", "codec": "h264", "priority": 5}
        )
        assert create_resp.status_code == 403
        assert create_resp.json()["error_code"] == "FORBIDDEN_ROLE"

        update_resp = auth_viewer_client.update_task(
            1, {"title": "Attempted Hijack", "codec": "h264", "priority": 5}
        )
        assert update_resp.status_code == 403

    def test_non_admin_role_cannot_delete_tasks(
        self, auth_qa_client: APIClient
    ) -> None:
        delete_resp = auth_qa_client.delete_task(1)
        assert delete_resp.status_code == 403
        assert delete_resp.json()["error_code"] == "ADMIN_REQUIRED"

