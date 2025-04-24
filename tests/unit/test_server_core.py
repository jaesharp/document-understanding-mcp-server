import pytest
from unittest.mock import patch, MagicMock, AsyncMock, ANY
import json

from src.document_understanding import server as pdf_server
from mcp import types  # For type checking

# Core server tests focusing on initialization, tool listing, etc.


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
async def test_main_function(mocker):
    """Test the main function startup sequence."""
    # Mock the stdio_server context manager
    mock_read_stream = MagicMock()
    mock_write_stream = MagicMock()

    # Create a mock context manager that yields our mock streams
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=(mock_read_stream, mock_write_stream))
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    # Patch the stdio_server function to return our mock context manager
    mocker.patch("mcp.server.stdio.stdio_server", return_value=mock_cm)

    # Mock the server.run method to do nothing
    mocker.patch.object(pdf_server.server, "run", AsyncMock())

    # Mock initialize_server_components
    mocker.patch("src.document_understanding.server.initialize_server_components")

    # Run the main function
    await pdf_server.main()

    # Verify context manager was entered and server.run was called
    mock_cm.__aenter__.assert_called_once()
    pdf_server.server.run.assert_called_once_with(
        mock_read_stream,
        mock_write_stream,
        ANY,  # We don't need to verify all details of InitializationOptions
    )


@pytest.mark.anyio(backend="asyncio")
async def test_handle_list_tools(mocker):
    """Test the handle_list_tools function."""
    # Mock tool registry list_tools method
    mock_tools = [
        types.Tool(name="tool1", description="Tool 1", inputSchema={}),
        types.Tool(name="tool2", description="Tool 2", inputSchema={}),
    ]
    mocker.patch.object(pdf_server.tool_registry, "list_tools", return_value=mock_tools)

    # Call the list_tools handler
    result = await pdf_server.handle_list_tools()

    # Verify the correct tools were returned
    assert len(result) == 2
    assert result[0].name == "tool1"
    assert result[1].name == "tool2"
