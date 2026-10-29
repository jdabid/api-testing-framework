"""Deterministic in-memory REST API Adapter for fast, reliable CI/CD execution."""

import io
import json
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any
import requests
from requests.adapters import BaseAdapter


VALID_CODECS = {"h264", "prores_422", "openexr", "vp9"}
USERS_DB = {
    "admin_qa": ("AdminPass123!", "admin"),
    "cristian_sdet": ("SdetPass123!", "qa_engineer"),
    "guest_viewer": ("ViewerPass123!", "viewer"),
}


class LocalRESTAdapter(BaseAdapter):
    """Custom requests adapter simulating a stateful RESTful microservice."""

    def __init__(self) -> None:
        super().__init__()
        self.reset_state()

    def reset_state(self) -> None:
        """Reset in-memory database and tokens before each test."""
        self.tokens: Dict[str, Dict[str, str]] = {}
        self.next_id: int = 3
        self.tasks: Dict[int, Dict[str, Any]] = {
            1: {
                "id": 1,
                "title": "Render Shot 010 Main Sequence",
                "codec": "prores_422",
                "priority": 8,
                "status": "queued",
                "owner": "cristian_sdet",
                "created_at": "2026-10-29T12:00:00Z",
            },
            2: {
                "id": 2,
                "title": "E2E Smoke Suite Execution",
                "codec": "h264",
                "priority": 5,
                "status": "completed",
                "owner": "admin_qa",
                "created_at": "2026-10-29T12:05:00Z",
            },
        }

    def _build_response(
        self, request: requests.PreparedRequest, status_code: int, payload: Any
    ) -> requests.Response:
        resp = requests.Response()
        resp.status_code = status_code
        resp.headers["Content-Type"] = "application/json"
        resp.request = request
        resp.url = request.url or ""
        if payload is None:
            resp.raw = io.BytesIO(b"")
            resp._content = b""
        else:
            raw_bytes = json.dumps(payload).encode("utf-8")
            resp.raw = io.BytesIO(raw_bytes)
            resp._content = raw_bytes
        return resp

    def _authenticate(self, request: requests.PreparedRequest) -> Dict[str, str] | None:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header.removeprefix("Bearer ").strip()
        return self.tokens.get(token)

    def send(
        self, request: requests.PreparedRequest, stream: bool = False, **kwargs: Any
    ) -> requests.Response:
        parsed = urllib.parse.urlparse(request.url or "")
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        method = (request.method or "GET").upper()

        body = {}
        if request.body:
            try:
                raw = (
                    request.body.decode("utf-8")
                    if isinstance(request.body, bytes)
                    else request.body
                )
                body = json.loads(raw)
            except Exception:
                return self._build_response(
                    request,
                    400,
                    {
                        "error_code": "MALFORMED_JSON",
                        "message": "Request body is not valid JSON.",
                    },
                )

        # 1. Healthcheck endpoint
        if path == "/api/v1/health" and method == "GET":
            return self._build_response(
                request, 200, {"status": "healthy", "service": "qa-pipeline-api"}
            )

        # 2. Auth Login endpoint
        if path == "/api/v1/auth/login" and method == "POST":
            username = body.get("username", "")
            password = body.get("password", "")
            if not username or not password:
                return self._build_response(
                    request,
                    400,
                    {
                        "error_code": "MISSING_CREDENTIALS",
                        "message": "Username and password are required.",
                    },
                )
            user_record = USERS_DB.get(username)
            if not user_record or user_record[0] != password:
                return self._build_response(
                    request,
                    401,
                    {
                        "error_code": "INVALID_CREDENTIALS",
                        "message": "Invalid username or password provided.",
                    },
                )
            role = user_record[1]
            token = f"jwt_eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.{username}.{role}"
            self.tokens[token] = {"username": username, "role": role}
            return self._build_response(
                request,
                200,
                {
                    "access_token": token,
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "role": role,
                },
            )

        # All endpoints below require Bearer JWT authentication
        user_ctx = self._authenticate(request)
        if not user_ctx:
            return self._build_response(
                request,
                401,
                {
                    "error_code": "UNAUTHORIZED",
                    "message": "Missing, expired, or invalid Bearer token.",
                },
            )

        # 3. Collection endpoint: /api/v1/tasks
        if path == "/api/v1/tasks":
            if method == "GET":
                page = int(query.get("page", ["1"])[0])
                per_page = int(query.get("per_page", ["10"])[0])
                if page < 1 or per_page < 1 or per_page > 100:
                    return self._build_response(
                        request,
                        422,
                        {
                            "error_code": "INVALID_PAGINATION",
                            "message": "Pagination parameters out of allowed bounds.",
                        },
                    )
                all_items = list(self.tasks.values())
                start = (page - 1) * per_page
                paged = all_items[start : start + per_page]
                return self._build_response(
                    request,
                    200,
                    {
                        "items": paged,
                        "total": len(all_items),
                        "page": page,
                        "per_page": per_page,
                    },
                )

            if method == "POST":
                if user_ctx["role"] == "viewer":
                    return self._build_response(
                        request,
                        403,
                        {
                            "error_code": "FORBIDDEN_ROLE",
                            "message": "Role 'viewer' is not allowed to create tasks.",
                        },
                    )
                error = self._validate_task_payload(body)
                if error:
                    return self._build_response(request, 422, error)

                task_id = self.next_id
                self.next_id += 1
                new_task = {
                    "id": task_id,
                    "title": body["title"].strip(),
                    "codec": body["codec"],
                    "priority": body["priority"],
                    "status": body.get("status", "queued"),
                    "owner": user_ctx["username"],
                    "created_at": datetime.now(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                }
                self.tasks[task_id] = new_task
                return self._build_response(request, 201, new_task)

        # 4. Single item endpoint: /api/v1/tasks/<id>
        if path.startswith("/api/v1/tasks/"):
            raw_id = path.removeprefix("/api/v1/tasks/")
            if not raw_id.isdigit():
                return self._build_response(
                    request,
                    400,
                    {
                        "error_code": "INVALID_TASK_ID",
                        "message": "Task ID must be a positive integer.",
                    },
                )
            task_id = int(raw_id)
            existing = self.tasks.get(task_id)

            if method == "GET":
                if not existing:
                    return self._build_response(
                        request,
                        404,
                        {
                            "error_code": "TASK_NOT_FOUND",
                            "message": f"Task with ID {task_id} was not found.",
                        },
                    )
                return self._build_response(request, 200, existing)

            if method == "PUT":
                if user_ctx["role"] == "viewer":
                    return self._build_response(
                        request,
                        403,
                        {
                            "error_code": "FORBIDDEN_ROLE",
                            "message": "Insufficient permissions to update tasks.",
                        },
                    )
                if not existing:
                    return self._build_response(
                        request,
                        404,
                        {
                            "error_code": "TASK_NOT_FOUND",
                            "message": f"Task with ID {task_id} was not found.",
                        },
                    )
                error = self._validate_task_payload(body)
                if error:
                    return self._build_response(request, 422, error)

                existing.update(
                    {
                        "title": body["title"].strip(),
                        "codec": body["codec"],
                        "priority": body["priority"],
                        "status": body.get("status", existing["status"]),
                    }
                )
                return self._build_response(request, 200, existing)

            if method == "DELETE":
                if user_ctx["role"] != "admin":
                    return self._build_response(
                        request,
                        403,
                        {
                            "error_code": "ADMIN_REQUIRED",
                            "message": "Only admin users can delete tasks.",
                        },
                    )
                if not existing:
                    return self._build_response(
                        request,
                        404,
                        {
                            "error_code": "TASK_NOT_FOUND",
                            "message": f"Task with ID {task_id} was not found.",
                        },
                    )
                del self.tasks[task_id]
                return self._build_response(request, 204, None)

        return self._build_response(
            request,
            404,
            {"error_code": "ENDPOINT_NOT_FOUND", "message": "Route does not exist."},
        )

    @staticmethod
    def _validate_task_payload(body: Dict[str, Any]) -> Dict[str, str] | None:
        title = body.get("title")
        codec = body.get("codec")
        priority = body.get("priority")

        if not isinstance(title, str) or len(title.strip()) < 3 or len(title.strip()) > 120:
            return {
                "error_code": "VALIDATION_ERROR",
                "message": "Field 'title' must be a string between 3 and 120 characters.",
            }
        if codec not in VALID_CODECS:
            return {
                "error_code": "UNSUPPORTED_CODEC",
                "message": f"Field 'codec' must be one of {sorted(VALID_CODECS)}.",
            }
        if not isinstance(priority, int) or isinstance(priority, bool) or not (1 <= priority <= 10):
            return {
                "error_code": "INVALID_PRIORITY",
                "message": "Field 'priority' must be an integer between 1 and 10.",
            }
        return None

    def close(self) -> None:
        pass

