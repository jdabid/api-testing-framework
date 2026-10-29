"""Boundary Value Analysis (BVA), Equivalence Partitioning, and negative edge cases."""

import pytest
from client.api_client import APIClient


@pytest.mark.bva
class TestBoundaryValuesAndEdgeCases:
    """Parameterized BVA and resilience tests for input validation."""

    @pytest.mark.parametrize(
        "priority_value,expected_status",
        [
            (0, 422),    # Just below minimum boundary (min = 1)
            (1, 201),    # Exact minimum boundary
            (2, 201),    # Just above minimum boundary
            (5, 201),    # Nominal middle value
            (9, 201),    # Just below maximum boundary
            (10, 201),   # Exact maximum boundary (max = 10)
            (11, 422),   # Just above maximum boundary
            (-5, 422),   # Negative integer partition
            ("5", 422),  # Invalid type (string instead of int)
            (True, 422), # Invalid type (boolean instead of int)
        ],
    )
    def test_task_priority_boundary_value_analysis(
        self, auth_qa_client: APIClient, priority_value: object, expected_status: int
    ) -> None:
        payload = {
            "title": "BVA Priority Test Task",
            "codec": "h264",
            "priority": priority_value,
        }
        response = auth_qa_client.create_task(payload)
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "title_value,expected_status",
        [
            ("", 422),             # Empty string
            ("ab", 422),           # 2 chars (below min=3)
            ("abc", 201),          # 3 chars (exact minimum boundary)
            ("A" * 120, 201),      # 120 chars (exact maximum boundary)
            ("A" * 121, 422),      # 121 chars (above max=120)
            ("   ", 422),          # Whitespace-only string
        ],
    )
    def test_task_title_length_boundaries(
        self, auth_qa_client: APIClient, title_value: str, expected_status: int
    ) -> None:
        payload = {
            "title": title_value,
            "codec": "prores_422",
            "priority": 5,
        }
        response = auth_qa_client.create_task(payload)
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "invalid_codec",
        ["avi_legacy", "mp3", "", None, 12345, "H264_UPPERCASE"],
    )
    def test_unsupported_media_codecs_return_422(
        self, auth_qa_client: APIClient, invalid_codec: object
    ) -> None:
        payload = {
            "title": "Codec Validation Check",
            "codec": invalid_codec,
            "priority": 4,
        }
        response = auth_qa_client.create_task(payload)
        assert response.status_code == 422
        assert response.json()["error_code"] == "UNSUPPORTED_CODEC"

    @pytest.mark.parametrize(
        "page,per_page",
        [
            (0, 10),
            (-1, 10),
            (1, 0),
            (1, 101),
        ],
    )
    def test_invalid_pagination_bounds_return_422(
        self, auth_qa_client: APIClient, page: int, per_page: int
    ) -> None:
        response = auth_qa_client.list_tasks(page=page, per_page=per_page)
        assert response.status_code == 422
        assert response.json()["error_code"] == "INVALID_PAGINATION"

    def test_malformed_non_integer_task_id_returns_400(
        self, auth_qa_client: APIClient
    ) -> None:
        response = auth_qa_client.get_task("drop-table-tasks")
        assert response.status_code == 400
        assert response.json()["error_code"] == "INVALID_TASK_ID"

