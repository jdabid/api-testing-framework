"""Pytest fixtures for API authentication, session isolation, and test data."""

import pytest
from client.api_client import APIClient


@pytest.fixture
def api_client() -> APIClient:
    """Provides a fresh, unauthenticated APIClient with clean state per test."""
    client = APIClient()
    client.adapter.reset_state()
    return client


@pytest.fixture
def auth_qa_client(api_client: APIClient) -> APIClient:
    """Provides an APIClient authenticated as a QA Engineer ('cristian_sdet')."""
    resp = api_client.login("cristian_sdet", "SdetPass123!")
    assert resp.status_code == 200
    return api_client


@pytest.fixture
def auth_admin_client(api_client: APIClient) -> APIClient:
    """Provides an APIClient authenticated as an Admin ('admin_qa')."""
    resp = api_client.login("admin_qa", "AdminPass123!")
    assert resp.status_code == 200
    return api_client


@pytest.fixture
def auth_viewer_client(api_client: APIClient) -> APIClient:
    """Provides an APIClient authenticated as a read-only Viewer ('guest_viewer')."""
    resp = api_client.login("guest_viewer", "ViewerPass123!")
    assert resp.status_code == 200
    return api_client

