"""Tests for server capabilities validation."""

import pytest
from unittest.mock import patch, MagicMock
import json

from src.document_understanding import server as pdf_server
from mcp import types


@pytest.mark.anyio(backend="asyncio")
@patch("src.document_understanding.server.ALLOW_ANY_PATH", True)
@patch.dict(pdf_server.SERVER_CAPABILITIES, {"search_functionality": False}, clear=True)
async def test_handle_call_tool_search_capability_missing(mocker, test_pdfs_setup):
    """Test calling search_pdf_text when capability is missing returns error response."""
    # Justification: Verify capability check prevents tool execution.
    # Use a path from the setup fixture
    args = {"pdf_path": str(test_pdfs_setup["text"]), "query": "test"}

    response = await pdf_server.handle_call_tool(name="search_pdf_text", arguments=args)

    # Verify response is a TextContent with error response json
    assert len(response) == 1
    assert response[0].type == "text"

    # Parse the JSON and verify error fields
    error_data = json.loads(response[0].text)
    assert error_data["status"] == "error"
    assert error_data["error_code"] == "missing_capabilities"
    assert "Required capabilities missing" in error_data["message"]
    assert "search_functionality" in error_data["message"]
    assert "search_functionality" in str(
        error_data["error_details"]["missing_capabilities"]
    )


@pytest.mark.anyio(backend="trio")  # Also ensure this test is covered by trio
@patch(
    "src.document_understanding.server.ALLOW_ANY_PATH", True
)  # Allow any path for this test
@patch.dict(
    pdf_server.SERVER_CAPABILITIES, {"search_functionality": False}, clear=True
)  # Disable search
async def test_handle_call_tool_search_capability_missing_trio(
    mocker, test_pdfs_setup
):  # Renamed and use correct fixture
    """Test calling search_pdf_text when capability is missing returns error response (Trio)."""
    # Justification: Verify capability check prevents tool execution for Trio backend.
    args = {
        "pdf_path": str(test_pdfs_setup["text"]),
        "query": "test",
    }  # Use a path from the setup fixture

    response = await pdf_server.handle_call_tool(name="search_pdf_text", arguments=args)

    # Verify response is a TextContent with error response json
    assert len(response) == 1
    assert response[0].type == "text"

    # Parse the JSON and verify error fields
    error_data = json.loads(response[0].text)
    assert error_data["status"] == "error"
    assert error_data["error_code"] == "missing_capabilities"
    assert "Required capabilities missing" in error_data["message"]
    assert "search_functionality" in error_data["message"]
    assert "search_functionality" in str(
        error_data["error_details"]["missing_capabilities"]
    ) 