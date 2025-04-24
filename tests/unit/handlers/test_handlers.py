import pytest
from unittest.mock import patch, MagicMock, ANY
import json
import os

from src.document_understanding import server as pdf_server
from src.document_understanding.models import (
    TextContentResponse,
    MetadataResponse,
    SearchResponse,
    LayoutResponse,
    ImageExtractionResponse,
    TableExtractionResponse,
    LanguageDetectionResponse,
    OutlineResponse,
    WorkingDirectoryResponse,
)


# Tests for successful tool calls


@pytest.mark.anyio(backend="asyncio")
@patch("src.document_understanding.server.ALLOW_ANY_PATH", True)
@patch.dict(pdf_server.SERVER_CAPABILITIES, {"search_functionality": True}, clear=True)
async def test_handle_call_tool_extract_contents_success(mocker):
    """Test successful extraction of PDF contents."""
    # Create a mock extractor with a successful response
    mock_extractor = MagicMock()
    mock_extractor.extract_content.return_value = [
        {"page": 1, "content": "Sample text content"}
    ]
    # Patch get_extractor to return our mock
    mocker.patch(
        "src.document_understanding.server.get_extractor", return_value=mock_extractor
    )

    # Mock the PathValidator to avoid file not found issues
    mocker.patch(
        "src.document_understanding.server.PathValidator.validate_and_resolve_path",
        return_value="/mocked/path/dummy.pdf",
    )

    response = await pdf_server.handle_call_tool(
        name="extract_pdf_contents", arguments={"pdf_path": "dummy.pdf"}
    )

    # Verify response is a TextContent with success response json
    assert len(response) == 1
    assert response[0].type == "text"

    # Parse the JSON and verify success fields
    response_data = json.loads(response[0].text)
    assert response_data["status"] == "success"
    assert "data" in response_data
    assert "pages" in response_data["data"]
    assert isinstance(response_data["data"]["pages"], list)


@pytest.mark.anyio(backend="asyncio")
@patch("src.document_understanding.server.ALLOW_ANY_PATH", True)
@patch.dict(pdf_server.SERVER_CAPABILITIES, {"search_functionality": True}, clear=True)
async def test_handle_call_tool_extract_metadata_success(mocker):
    """Test successful extraction of PDF metadata."""
    # Create a mock extractor with a successful response
    mock_extractor = MagicMock()
    mock_extractor.extract_metadata.return_value = {
        "page_count": 1,
        "metadata": {"Title": "Test Document"},
        "has_embedded_images": True,
        "has_vector_drawings": False,
    }
    # Patch get_extractor to return our mock
    mocker.patch(
        "src.document_understanding.server.get_extractor", return_value=mock_extractor
    )

    # Mock the PathValidator to avoid file not found issues
    mocker.patch(
        "src.document_understanding.server.PathValidator.validate_and_resolve_path",
        return_value="/mocked/path/dummy.pdf",
    )

    response = await pdf_server.handle_call_tool(
        name="extract_pdf_metadata", arguments={"pdf_path": "dummy.pdf"}
    )

    # Verify response is a TextContent with success response json
    assert len(response) == 1
    assert response[0].type == "text"

    # Parse the JSON and verify success fields
    response_data = json.loads(response[0].text)
    assert response_data["status"] == "success"
    assert "data" in response_data
    assert "metadata" in response_data["data"]
    assert "page_count" in response_data["data"]
    assert isinstance(response_data["data"]["metadata"], dict)


@pytest.mark.anyio(backend="asyncio")
@patch("src.document_understanding.server.ALLOW_ANY_PATH", True)
@patch.dict(pdf_server.SERVER_CAPABILITIES, {"search_functionality": True}, clear=True)
async def test_handle_call_tool_search_text_success(mocker):
    """Test successful search in PDF text."""
    # Create a mock extractor with a successful response
    mock_extractor = MagicMock()
    mock_extractor.search_text.return_value = {
        "results": [{"page": 1, "rect": {"x0": 0, "y0": 0, "x1": 10, "y1": 10}}],
        "query": "test",
        "total_matches": 1,
    }
    # Patch get_extractor to return our mock
    mocker.patch(
        "src.document_understanding.server.get_extractor", return_value=mock_extractor
    )

    # Mock the PathValidator to avoid file not found issues
    mocker.patch(
        "src.document_understanding.server.PathValidator.validate_and_resolve_path",
        return_value="/mocked/path/dummy.pdf",
    )

    response = await pdf_server.handle_call_tool(
        name="search_pdf_text",
        arguments={
            "pdf_path": "dummy.pdf",
            "query": "test",  # Simple query that should match something
        },
    )

    # Verify response is a TextContent with success response json
    assert len(response) == 1
    assert response[0].type == "text"

    # Parse the JSON and verify success fields
    response_data = json.loads(response[0].text)
    assert response_data["status"] == "success"
    assert "data" in response_data
    assert "results" in response_data["data"]
    assert "query" in response_data["data"]
    assert "total_matches" in response_data["data"]
    assert response_data["data"]["query"] == "test"
    assert isinstance(response_data["data"]["results"], list)


@pytest.mark.anyio(backend="asyncio")
@patch("src.document_understanding.server.ALLOW_ANY_PATH", True)
@patch.dict(pdf_server.SERVER_CAPABILITIES, {"search_functionality": True}, clear=True)
async def test_handle_call_tool_extract_layout_success(mocker, test_pdfs_setup):
    """Test successful extraction of PDF layout."""
    # Create a mock extractor
    mock_extractor = MagicMock()
    # Set up the mock to return a minimal but valid layout response
    mock_extractor.extract_layout.return_value = [
        {"page_number": 1, "text_blocks": [], "drawings": [], "images": []}
    ]
    # Patch get_extractor to return our mock
    mocker.patch(
        "src.document_understanding.server.get_extractor", return_value=mock_extractor
    )

    response = await pdf_server.handle_call_tool(
        name="extract_pdf_layout",
        arguments={
            "pdf_path": "dummy.pdf",
            "include_images": True,
            "include_drawings": True,
        },
    )

    # Verify response is a TextContent with success response json
    assert len(response) == 1
    assert response[0].type == "text"

    # Parse the JSON and verify success fields
    response_data = json.loads(response[0].text)
    assert response_data["status"] == "success"
    assert "data" in response_data
    assert "layout" in response_data["data"]
    assert "include_images" in response_data["data"]
    assert "include_drawings" in response_data["data"]
    assert response_data["data"]["include_images"] == True
    assert response_data["data"]["include_drawings"] == True
    assert isinstance(response_data["data"]["layout"], list)

    # Verify our mock was called with the right arguments
    mock_extractor.extract_layout.assert_called_once_with(
        ANY,  # The pdf_path will be resolved
        None,  # No pages specified
        include_images=True,
        include_drawings=True,
        detail_level=None,
    )
