"""Test for the document understanding server."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock, ANY
import json
import os

# Import the server instance and methods to test/patch
from src.document_understanding import server as pdf_server
from mcp import types  # For type checking

# Configuration based on tests
pdf_server.BASE_PATH = None


@pytest.fixture(autouse=True)
def reset_server_state():
    """Reset global state before each test."""
    # Reset capabilities if needed, or rely on mocker per test
    pass


@pytest.mark.anyio(backend="asyncio")
async def test_main_function(mocker):
    """Test the main function of the server."""
    # Mock MCP server interactions to test main() startup sequence without network/stdio
    mock_stdio_server = AsyncMock()
    mock_read_stream = AsyncMock()
    mock_write_stream = AsyncMock()
    mock_stdio_server.__aenter__.return_value = (mock_read_stream, mock_write_stream)
    mock_stdio_server.__aexit__.return_value = None
    mocker.patch("mcp.server.stdio.stdio_server", return_value=mock_stdio_server)
    
    # Mock server.run to prevent actual server execution
    mock_server_run = AsyncMock()
    mocker.patch("src.document_understanding.server.server.run", mock_server_run)
    
    # Test main function
    await pdf_server.main()
    
    # Verify stdio_server was called and server.run was called
    mock_stdio_server.__aenter__.assert_called_once()
    mock_server_run.assert_called_once()


@pytest.mark.anyio(backend="asyncio")
@patch.dict(pdf_server.SERVER_CAPABILITIES, {"search_functionality": True, "java_runtime": True}, clear=True)
async def test_handle_list_tools(mocker):
    """Test list_tools returns the expected tool definitions."""
    # Get the tools list
    tools_list = await pdf_server.handle_list_tools()
    
    # Verify it's a list
    assert isinstance(tools_list, list)
    
    # Check for expected tool names in the response
    tool_names = [tool.name for tool in tools_list]
    assert "extract_pdf_contents" in tool_names
    assert "extract_pdf_metadata" in tool_names
    assert "search_pdf_text" in tool_names
    assert "extract_tables" in tool_names
    
    # Check tool definition structure
    for tool in tools_list:
        assert "name" in tool.__dict__
        assert "description" in tool.__dict__
        assert "inputSchema" in tool.__dict__
