import pytest
from unittest.mock import patch, MagicMock, ANY
import json

from src.document_understanding import server as pdf_server
from mcp import types  # For type checking


# Fixture to initialize the extractor before tests
@pytest.fixture(autouse=True)
def initialize_extractor(monkeypatch):
    """Initialize server components and extractor before each test."""
    # Create a mock extractor
    mock_extractor = MagicMock()

    # Set the extractor on the server module
    monkeypatch.setattr(pdf_server, "extractor", mock_extractor)

    # Initialize server components
    pdf_server.initialize_server_components()

    return mock_extractor


# Tests for error handling in tool calls


@pytest.mark.anyio(backend="asyncio")
@patch("src.document_understanding.server.ALLOW_ANY_PATH", True)
@patch(
    "src.document_understanding.server.extractor.extract_content",
    side_effect=FileNotFoundError("File went missing!"),
)
async def test_tool_extract_content_handles_file_not_found(mock_extract):
    """Test handling of FileNotFoundError when extracting content."""
    response = await pdf_server.handle_call_tool(
        name="extract_pdf_contents", arguments={"pdf_path": "nonexistent.pdf"}
    )

    # Verify response is a TextContent with error response json
    assert len(response) == 1
    assert response[0].type == "text"

    # Parse the JSON and verify error fields
    error_data = json.loads(response[0].text)
    assert error_data["status"] == "error"
    assert error_data["error_code"] == "file_not_found"
    assert "File went missing!" in error_data["message"]

    # Verify our mock was called
    mock_extract.assert_called_once()


@pytest.mark.anyio(backend="asyncio")
@patch("src.document_understanding.server.ALLOW_ANY_PATH", True)
@patch(
    "src.document_understanding.server.extractor.extract_content",
    side_effect=ValueError("Bad page spec!"),
)
async def test_tool_extract_content_handles_value_error(mock_extract):
    """Test handling of ValueError when extracting content."""
    response = await pdf_server.handle_call_tool(
        name="extract_pdf_contents",
        arguments={"pdf_path": "dummy.pdf", "pages": "invalid"},
    )

    # Verify response is a TextContent with error response json
    assert len(response) == 1
    assert response[0].type == "text"

    # Parse the JSON and verify error fields
    error_data = json.loads(response[0].text)
    assert error_data["status"] == "error"
    assert error_data["error_code"] == "value_error"
    assert "Bad page spec!" in error_data["message"]

    # Verify our mock was called
    mock_extract.assert_called_once()


@pytest.mark.anyio(backend="asyncio")
@patch("src.document_understanding.server.ALLOW_ANY_PATH", True)
@patch(
    "src.document_understanding.server.extractor.extract_content",
    side_effect=Exception("Generic PDF error!"),
)
async def test_tool_extract_content_handles_generic_exception(mock_extract):
    """Test handling of generic Exception when extracting content."""
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
    mock_extract.assert_called_once()


@pytest.mark.anyio(backend="asyncio")
@patch("src.document_understanding.server.ALLOW_ANY_PATH", True)
@patch(
    "src.document_understanding.server.extractor.extract_metadata",
    side_effect=FileNotFoundError("Metadata file missing!"),
)
async def test_tool_extract_metadata_handles_file_not_found(mock_extract):
    """Test handling of FileNotFoundError when extracting metadata."""
    response = await pdf_server.handle_call_tool(
        name="extract_pdf_metadata", arguments={"pdf_path": "nonexistent.pdf"}
    )

    # Verify response is a TextContent with error response json
    assert len(response) == 1
    assert response[0].type == "text"

    # Parse the JSON and verify error fields
    error_data = json.loads(response[0].text)
    assert error_data["status"] == "error"
    assert error_data["error_code"] == "file_not_found"
    assert "Metadata file missing!" in error_data["message"]

    # Verify our mock was called
    mock_extract.assert_called_once()


@pytest.mark.anyio(backend="asyncio")
@patch("src.document_understanding.server.ALLOW_ANY_PATH", True)
@patch(
    "src.document_understanding.server.extractor.search_text",
    side_effect=FileNotFoundError("Search file missing!"),
)
@patch.dict(pdf_server.SERVER_CAPABILITIES, {"search_functionality": True}, clear=True)
async def test_tool_search_text_handles_file_not_found(mock_extract):
    """Test handling of FileNotFoundError when searching text."""
    response = await pdf_server.handle_call_tool(
        name="search_pdf_text",
        arguments={"pdf_path": "nonexistent.pdf", "query": "test"},
    )

    # Verify response is a TextContent with error response json
    assert len(response) == 1
    assert response[0].type == "text"

    # Parse the JSON and verify error fields
    error_data = json.loads(response[0].text)
    assert error_data["status"] == "error"
    assert error_data["error_code"] == "file_not_found"
    assert "Search file missing!" in error_data["message"]

    # Verify our mock was called
    mock_extract.assert_called_once()


@pytest.mark.anyio(backend="asyncio")
@patch("src.document_understanding.server.ALLOW_ANY_PATH", True)
@patch(
    "src.document_understanding.server.extractor.extract_layout",
    side_effect=FileNotFoundError("Layout file missing!"),
)
async def test_tool_extract_layout_handles_file_not_found(mock_extract):
    """Test handling of FileNotFoundError when extracting layout."""
    response = await pdf_server.handle_call_tool(
        name="extract_pdf_layout", arguments={"pdf_path": "nonexistent.pdf"}
    )

    # Verify response is a TextContent with error response json
    assert len(response) == 1
    assert response[0].type == "text"

    # Parse the JSON and verify error fields
    error_data = json.loads(response[0].text)
    assert error_data["status"] == "error"
    assert error_data["error_code"] == "file_not_found"
    assert "Layout file missing!" in error_data["message"]

    # Verify our mock was called
    mock_extract.assert_called_once()


@pytest.mark.anyio(backend="asyncio")
@patch("src.document_understanding.server.ALLOW_ANY_PATH", True)
@patch(
    "src.document_understanding.server.extractor.extract_images",
    side_effect=FileNotFoundError("Image file missing!"),
)
async def test_tool_extract_images_handles_file_not_found(mock_extract):
    """Test handling of FileNotFoundError when extracting images."""
    response = await pdf_server.handle_call_tool(
        name="extract_images", arguments={"pdf_path": "nonexistent.pdf"}
    )

    # Verify response is a TextContent with error response json
    assert len(response) == 1
    assert response[0].type == "text"

    # Parse the JSON and verify error fields
    error_data = json.loads(response[0].text)
    assert error_data["status"] == "error"
    assert error_data["error_code"] == "file_not_found"
    assert "Image file missing!" in error_data["message"]

    # Verify our mock was called
    mock_extract.assert_called_once()


@pytest.mark.anyio(backend="asyncio")
@patch("src.document_understanding.server.ALLOW_ANY_PATH", True)
@patch.dict(pdf_server.SERVER_CAPABILITIES, {"java_runtime": True}, clear=True)
async def test_tool_extract_tables_handles_generic_exception(mocker):
    """Test handling of generic exception when extracting tables."""
    # Create a mock extractor instance
    mock_extractor = MagicMock()
    # Configure extract_tables to raise a generic Exception
    mock_extractor.extract_tables.side_effect = Exception("Tables extraction failed!")
    # Patch get_extractor to return our mock
    mocker.patch(
        "src.document_understanding.server.get_extractor", return_value=mock_extractor
    )

    response = await pdf_server.handle_call_tool(
        name="extract_tables", arguments={"pdf_path": "dummy.pdf"}
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
    mock_extractor.extract_tables.assert_called_once()


@pytest.mark.anyio(backend="asyncio")
@patch("src.document_understanding.server.ALLOW_ANY_PATH", True)
@patch(
    "src.document_understanding.server.extractor.detect_language",
    side_effect=FileNotFoundError("Langdetect file missing!"),
)
async def test_tool_detect_language_handles_file_not_found(mock_extract):
    """Test handling of FileNotFoundError when detecting language."""
    response = await pdf_server.handle_call_tool(
        name="detect_language", arguments={"pdf_path": "nonexistent.pdf"}
    )

    # Verify response is a TextContent with error response json
    assert len(response) == 1
    assert response[0].type == "text"

    # Parse the JSON and verify error fields
    error_data = json.loads(response[0].text)
    assert error_data["status"] == "error"
    assert error_data["error_code"] == "file_not_found"
    assert "Langdetect file missing!" in error_data["message"]

    # Verify our mock was called
    mock_extract.assert_called_once()


@pytest.fixture
def mock_outline_extractor():
    """Create a mock extractor with extract_outline configured to raise FileNotFoundError."""
    mock_extractor = MagicMock()
    mock_extractor.extract_outline.side_effect = FileNotFoundError(
        "Outline file missing!"
    )
    return mock_extractor


@pytest.mark.anyio(backend="asyncio")
@patch("src.document_understanding.server.ALLOW_ANY_PATH", True)
@patch("src.document_understanding.handlers.get_extractor")
async def test_tool_extract_outline_handles_file_not_found(
    mock_get_extractor, mock_outline_extractor
):
    """Test handling of FileNotFoundError when extracting outline."""
    # Configure the mock get_extractor to return our mock_outline_extractor
    mock_get_extractor.return_value = mock_outline_extractor

    response = await pdf_server.handle_call_tool(
        name="extract_pdf_outline", arguments={"pdf_path": "nonexistent.pdf"}
    )

    # Verify response is a TextContent with error response json
    assert len(response) == 1
    assert response[0].type == "text"

    # Parse the JSON and verify error fields
    error_data = json.loads(response[0].text)
    assert error_data["status"] == "error"
    assert error_data["error_code"] == "file_not_found"
    assert "Outline file missing!" in error_data["message"]

    # Verify our mock was called
    mock_outline_extractor.extract_outline.assert_called_once()


@pytest.fixture
def mock_outline_extractor_generic_exception():
    """Create a mock extractor with extract_outline configured to raise a generic Exception."""
    mock_extractor = MagicMock()
    mock_extractor.extract_outline.side_effect = Exception("Outline extraction failed!")
    return mock_extractor


@pytest.mark.anyio(backend="asyncio")
@patch("src.document_understanding.server.ALLOW_ANY_PATH", True)
@patch("src.document_understanding.handlers.get_extractor")
async def test_tool_extract_outline_handles_generic_exception(
    mock_get_extractor, mock_outline_extractor_generic_exception
):
    """Test handling of generic exception when extracting outline."""
    # Configure the mock get_extractor to return our mock_outline_extractor
    mock_get_extractor.return_value = mock_outline_extractor_generic_exception

    response = await pdf_server.handle_call_tool(
        name="extract_pdf_outline", arguments={"pdf_path": "dummy.pdf"}
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
    mock_outline_extractor_generic_exception.extract_outline.assert_called_once()
