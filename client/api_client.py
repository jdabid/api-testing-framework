"""Reusable API Client wrapping requests.Session for clean endpoint testing."""

from typing import Any, Dict, Optional
import requests
from client.local_service import LocalRESTAdapter


class APIClient:
    """High-level HTTP client for interacting with the QA & Pipeline REST API."""

    def __init__(self, base_url: str = "http://api.capyzendev.local") -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.adapter = LocalRESTAdapter()
        self.session.mount("http://api.capyzendev.local", self.adapter)
        self.token: Optional[str] = None

    def set_token(self, token: Optional[str]) -> None:
        """Configure or clear the Authorization Bearer token header."""
        self.token = token
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            self.session.headers.pop("Authorization", None)

    def login(self, username: str, password: str) -> requests.Response:
        """Authenticate user and automatically store token if successful."""
        response = self.session.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        if response.status_code == 200:
            data = response.json()
            self.set_token(data.get("access_token"))
        return response

    def health_check(self) -> requests.Response:
        """GET /api/v1/health"""
        return self.session.get(f"{self.base_url}/api/v1/health")

    def list_tasks(self, page: int = 1, per_page: int = 10) -> requests.Response:
        """GET /api/v1/tasks"""
        return self.session.get(
            f"{self.base_url}/api/v1/tasks",
            params={"page": page, "per_page": per_page},
        )

    def get_task(self, task_id: int | str) -> requests.Response:
        """GET /api/v1/tasks/{task_id}"""
        return self.session.get(f"{self.base_url}/api/v1/tasks/{task_id}")

    def create_task(self, payload: Dict[str, Any]) -> requests.Response:
        """POST /api/v1/tasks"""
        return self.session.post(f"{self.base_url}/api/v1/tasks", json=payload)

    def update_task(self, task_id: int | str, payload: Dict[str, Any]) -> requests.Response:
        """PUT /api/v1/tasks/{task_id}"""
        return self.session.put(
            f"{self.base_url}/api/v1/tasks/{task_id}", json=payload
        )

    def delete_task(self, task_id: int | str) -> requests.Response:
        """DELETE /api/v1/tasks/{task_id}"""
        return self.session.delete(f"{self.base_url}/api/v1/tasks/{task_id}")

