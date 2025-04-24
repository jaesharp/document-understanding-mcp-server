"""Tests for basic server error handling in the document understanding server."""

import pytest
from unittest.mock import patch, MagicMock
import json

from src.document_understanding import server as pdf_server
from src.document_understanding.extractor import PDFExtractor
from mcp import types


@pytest.mark.anyio(backend="asyncio")
async def test_handle_call_tool_missing_args():
    """Test that handle_call_tool properly handles missing arguments."""
    response = await pdf_server.handle_call_tool(name="test-tool", arguments=None)

    # Verify response is a TextContent with error response json
    assert len(response) == 1
    assert response[0].type == "text"

    # Parse the JSON and verify error fields
    error_data = json.loads(response[0].text)
    assert error_data["status"] == "error"
    assert error_data["error_code"] == "unknown_tool"
    assert "Unknown or unavailable tool" in error_data["message"]
    assert error_data["error_details"]["tool_name"] == "test-tool"


@pytest.mark.anyio(backend="asyncio")
async def test_handle_call_tool_missing_pdf_path():
    """Test handling of missing pdf_path argument."""
    # Pass some other argument to bypass the initial 'if not arguments' check
    response = await pdf_server.handle_call_tool(
        name="extract_pdf_contents", arguments={"other_arg": 123}
    )

    # Verify response is a TextContent with error response json
    assert len(response) == 1
    assert response[0].type == "text"

    # Parse the JSON and verify error fields
    error_data = json.loads(response[0].text)
    assert error_data["status"] == "error"
    assert error_data["error_code"] == "value_error"
    assert "pdf_path is required for extract_pdf_contents" in error_data["message"]


@pytest.mark.anyio(backend="asyncio")
@patch("src.document_understanding.server.ALLOW_ANY_PATH", True)
async def test_handle_call_tool_unknown_tool():
    """Test handling of an unknown tool."""
    response = await pdf_server.handle_call_tool(
        name="non_existent_tool", arguments={"pdf_path": "dummy"}
    )

    # Verify response is a TextContent with error response json
    assert len(response) == 1
    assert response[0].type == "text"

    # Parse the JSON and verify error fields
    error_data = json.loads(response[0].text)
    assert error_data["status"] == "error"
    assert error_data["error_code"] == "unknown_tool"
    assert "Unknown or unavailable tool" in error_data["message"]
    assert error_data["error_details"]["tool_name"] == "non_existent_tool"


@pytest.mark.anyio(backend="asyncio")
@patch("src.document_understanding.server.ALLOW_ANY_PATH", True)
async def test_handle_call_tool_extractor_value_error(mocker):
    """Test handling of ValueError raised by the extractor."""
    # Create a mock extractor instance
    mock_extractor = MagicMock(spec=PDFExtractor)
    # Configure extract_content to raise ValueError
    mock_extractor.extract_content.side_effect = ValueError("Extractor Value Error")
    # Patch get_extractor to return our mock
    mocker.patch(
        "src.document_understanding.server.get_extractor", return_value=mock_extractor
    )

    response = await pdf_server.handle_call_tool(
        name="extract_pdf_contents", arguments={"pdf_path": "dummy.pdf"}
    )

    # Verify response is a TextContent with error response json
    assert len(response) == 1
    assert response[0].type == "text"

    # Parse the JSON and verify error fields
    error_data = json.loads(response[0].text)
    assert error_data["status"] == "error"
    assert error_data["error_code"] == "value_error"
    assert "Extractor Value Error" in error_data["message"]

    # Verify our mock was called
    mock_extractor.extract_content.assert_called_once()


@pytest.mark.anyio(backend="asyncio")
@patch("src.document_understanding.server.ALLOW_ANY_PATH", True)
async def test_handle_call_tool_extractor_file_not_found(mocker):
    """Test handling of FileNotFoundError raised by the extractor."""
    # Create a mock extractor instance
    mock_extractor = MagicMock(spec=PDFExtractor)
    # Configure extract_content to raise FileNotFoundError
    mock_extractor.extract_content.side_effect = FileNotFoundError(
        "Extractor File Error"
    )
    # Patch get_extractor to return our mock
    mocker.patch(
        "src.document_understanding.server.get_extractor", return_value=mock_extractor
    )

    # Get the response instead of expecting an exception
    response = await pdf_server.handle_call_tool(
        name="extract_pdf_contents", arguments={"pdf_path": "dummy.pdf"}
    )

    # Verify response is a TextContent with error response json
    assert len(response) == 1
    assert response[0].type == "text"

    # Parse the JSON and verify error fields
    error_data = json.loads(response[0].text)
    assert error_data["status"] == "error"
    assert error_data["error_code"] == "file_not_found"
    assert "Extractor File Error" in error_data["message"]

    # Verify our mock was called
    mock_extractor.extract_content.assert_called_once()


@pytest.mark.anyio(backend="asyncio")
@patch.dict(pdf_server.SERVER_CAPABILITIES, {"java_runtime": True}, clear=True)
@patch("src.document_understanding.server.ALLOW_ANY_PATH", True)
async def test_handle_call_tool_extractor_runtime_error(mocker):
    """Test handling of RuntimeError raised by the extractor."""
    # Create a mock extractor instance
    mock_extractor = MagicMock(spec=PDFExtractor)
    # Configure extract_tables to raise RuntimeError
    mock_extractor.extract_tables.side_effect = RuntimeError("Extractor Runtime Error")
    # Patch get_extractor to return our mock
    mocker.patch(
        "src.document_understanding.server.get_extractor", return_value=mock_extractor
    )

    # Get the response instead of expecting an exception
    response = await pdf_server.handle_call_tool(
        name="extract_tables", arguments={"pdf_path": "dummy.pdf"}
    )

    # Verify response is a TextContent with error response json
    assert len(response) == 1
    assert response[0].type == "text"

    # Parse the JSON and verify error fields
    error_data = json.loads(response[0].text)
    assert error_data["status"] == "error"
    assert error_data["error_code"] == "runtime_error"
    assert "Extractor Runtime Error" in error_data["message"]

    # Verify our mock was called
    mock_extractor.extract_tables.assert_called_once()


@pytest.mark.anyio(backend="asyncio")
@patch("src.document_understanding.server.ALLOW_ANY_PATH", True)
async def test_handle_call_tool_extractor_generic_exception(mocker):
    """Test handling of generic Exception raised by the extractor."""
    # Create a mock extractor instance
    mock_extractor = MagicMock(spec=PDFExtractor)
    # Configure extract_content to raise Exception
    mock_extractor.extract_content.side_effect = Exception("Extractor Generic Error")
    # Patch get_extractor to return our mock
    mocker.patch(
        "src.document_understanding.server.get_extractor", return_value=mock_extractor
    )

    # Get the response instead of expecting an exception
    response = await pdf_server.handle_call_tool(
        name="extract_pdf_contents", arguments={"pdf_path": "dummy.pdf"}
    )

    # Verify response is a TextContent with error response json
    assert len(response) == 1
    assert response[0].type == "text"

    # Parse the JSON and verify error fields
    error_data = json.loads(response[0].text)
    assert error_data["status"] == "error"
    assert error_data["error_code"] == "server_error"
    assert "unexpected server error" in error_data["message"].lower()

    # Verify our mock was called
    mock_extractor.extract_content.assert_called_once() 