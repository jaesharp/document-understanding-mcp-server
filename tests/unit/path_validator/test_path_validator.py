import pytest
from unittest.mock import patch, MagicMock
import os
import json

from src.document_understanding.path_validator import PathValidator
from src.document_understanding import server as pdf_server


@pytest.mark.parametrize(
    "allow_any, base, input_path, expected_ok, expected_substr, expected_exception",
    [
        # --- Allow Any Path --- #
        (True, None, "doc.pdf", True, "doc.pdf", None),  # Relative
        (
            True,
            None,
            "/absolute/path/doc.pdf",
            True,
            "/absolute/path/doc.pdf",
            None,
        ),  # Absolute
        (
            True,
            None,
            "../outside.pdf",
            True,
            "outside.pdf",
            None,
        ),  # Traversal allowed when ANY path is ok
        # --- Base Path Restriction --- #
        (
            False,
            "/safe/base",
            "doc.pdf",
            True,
            "/safe/base/doc.pdf",
            None,
        ),  # Relative, inside
        (
            False,
            "/safe/base",
            "subdir/doc.pdf",
            True,
            "/safe/base/subdir/doc.pdf",
            None,
        ),  # Subdir, inside
        (
            False,
            "/safe/base",
            "/safe/base/doc.pdf",
            True,
            "/safe/base/doc.pdf",
            None,
        ),  # Absolute, inside
        (
            False,
            "/safe/base",
            "../base/doc.pdf",
            True,
            "/safe/base/doc.pdf",
            None,
        ),  # Resolves inside
        (
            False,
            "/safe/base",
            "../sibling/doc.pdf",
            False,
            "outside the allowed base directory",
            ValueError,
        ),  # Traversal, outside
        (
            False,
            "/safe/base",
            "/other/absolute/doc.pdf",
            False,
            "outside the allowed base directory",
            ValueError,
        ),  # Absolute, outside
        (
            False,
            "/safe/base/",
            "doc.pdf",
            True,
            "/safe/base/doc.pdf",
            None,
        ),  # Base with trailing slash
        (
            False,
            None,
            "doc.pdf",
            False,
            "Base path not set",
            RuntimeError,
        ),  # Error if base not set and restriction on
    ],
)
def test_validate_and_resolve_path(
    mocker,
    allow_any,
    base,
    input_path,
    expected_ok,
    expected_substr,
    expected_exception,
):
    """
    Test path validation and resolution with various inputs.

    This comprehensive test covers different scenarios for path validation:
    - Allowing any path (absolute, relative, traversal)
    - Base path restrictions (paths must be within base)
    - Path normalization and resolution behavior
    """
    # Create a PathValidator instance with the test params
    validator = PathValidator(allow_any_path=allow_any, base_path=base)

    if expected_ok:
        # Should succeed with path containing expected substring
        result = validator.validate_and_resolve_path(input_path)
        assert expected_substr in result
    else:
        # Should raise expected exception with substring in message
        with pytest.raises(expected_exception or ValueError) as excinfo:
            validator.validate_and_resolve_path(input_path)
        assert expected_substr in str(excinfo.value)


@pytest.mark.anyio(backend="asyncio")
@patch("src.document_understanding.server.ALLOW_ANY_PATH", False)  # Restriction ON
@patch("src.document_understanding.server.BASE_PATH", "/safe/base")
async def test_handle_call_tool_path_validation_fail_before_call(mocker):
    """Test that path validation fails before tool execution when path is outside allowed base."""
    # Path that would be outside the allowed base directory
    response = await pdf_server.handle_call_tool(
        name="extract_pdf_contents", arguments={"pdf_path": "/forbidden/path/doc.pdf"}
    )

    # Verify response is a TextContent with error response json
    assert len(response) == 1
    assert response[0].type == "text"

    # Parse the JSON and verify error fields
    error_data = json.loads(response[0].text)
    assert error_data["status"] == "error"
    assert error_data["error_code"] == "value_error"
    assert "outside the allowed base directory" in error_data["message"]


@pytest.mark.anyio(backend="asyncio")
async def test_handle_call_tool_invalid_pdf_path_type():
    """Test handling of invalid pdf_path type."""
    # Pass a non-string value as pdf_path
    response = await pdf_server.handle_call_tool(
        name="extract_pdf_contents", arguments={"pdf_path": 123}  # Not a string
    )

    # Verify response is a TextContent with error response json
    assert len(response) == 1
    assert response[0].type == "text"

    # Parse the JSON and verify error fields
    error_data = json.loads(response[0].text)
    assert error_data["status"] == "error"
    assert error_data["error_code"] == "value_error"
    assert "Missing or invalid required argument: pdf_path" in error_data["message"]
