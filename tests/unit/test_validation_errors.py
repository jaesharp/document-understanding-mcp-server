"""Tests for validation error handling in the document understanding server."""

import pytest
from unittest.mock import patch, MagicMock
import json
from pydantic import ValidationError

from src.document_understanding import server as pdf_server
from src.document_understanding.extractor import PDFExtractor


@pytest.mark.anyio(backend="asyncio")
@patch("src.document_understanding.server.ALLOW_ANY_PATH", True)
@patch("src.document_understanding.server.get_extractor")
async def test_handle_call_tool_pydantic_validation_error(mock_get_extractor):
    """Test handling of Pydantic validation error when extracting layout."""
    # Create a mock extractor instance
    mock_extractor = MagicMock()

    # We'll raise a different exception that's wrapped in a ValidationError via __cause__
    class ValidationTestError(Exception):
        def __init__(self):
            super().__init__("Test validation error")

    test_error = ValidationTestError()
    # Add the __cause__ attribute to simulate how ValidationError often appears wrapped
    test_error.__cause__ = ValidationError.from_exception_data(
        title="Validation Error",
        line_errors=[{"type": "missing", "loc": ["field"], "msg": "field required"}],
    )

    # Set up the side effect to raise this error
    mock_extractor.extract_layout.side_effect = test_error
    mock_get_extractor.return_value = mock_extractor

    # Call the tool
    response = await pdf_server.handle_call_tool(
        name="extract_pdf_layout",
        arguments={"pdf_path": "dummy.pdf", "ocr_strategy": "auto"},
    )

    # Verify the JSON structure
    assert len(response) == 1
    assert response[0].type == "text"
    error_data = json.loads(response[0].text)
    assert error_data["status"] == "error"
    assert error_data["error_code"] == "validation_error"
    assert "validation error" in error_data["message"].lower()

    # Verify the mock was called once
    mock_extractor.extract_layout.assert_called_once()


@pytest.mark.anyio(backend="asyncio")
@patch("src.document_understanding.server.ALLOW_ANY_PATH", False)  # Restriction ON
@patch("src.document_understanding.server.BASE_PATH", "/safe/base")
async def test_handle_call_tool_path_validation_fail_before_call(mocker):
    """Test path validation failure before tool call."""
    # Create a mock extractor
    mock_extractor = MagicMock(spec=PDFExtractor)
    # Patch get_extractor to return our mock
    mocker.patch(
        "src.document_understanding.server.get_extractor", return_value=mock_extractor
    )

    # Get the response directly
    response = await pdf_server.handle_call_tool(
        name="extract_pdf_contents", arguments={"pdf_path": "../unsafe/doc.pdf"}
    )

    # Verify response is a TextContent with error response json
    assert len(response) == 1
    assert response[0].type == "text"

    # Parse the JSON and verify error fields
    error_data = json.loads(response[0].text)
    assert error_data["status"] == "error"
    assert error_data["error_code"] == "value_error"
    assert "outside the allowed base directory" in error_data["message"]

    # The extractor method should never be called
    mock_extractor.extract_content.assert_not_called()
