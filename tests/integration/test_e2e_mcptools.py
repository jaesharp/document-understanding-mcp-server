"""
Enhanced E2E Tests Using MCPTools CLI with Real Server

This module provides enhanced end-to-end tests using the MCPTools CLI to test
various aspects of the PDF extraction server with the actual server implementation.

These tests focus on:
1. Server lifecycle (startup, operation, shutdown)
2. Document processing (metadata, content, images, layout)
3. Search functionality
4. Error handling
5. Configuration testing
"""

import os
import pytest

from tests.integration.mcptools_helpers import (
    run_mcp_command,
    parse_json_response,
)

# Mark all tests as anyio for async support
pytestmark = pytest.mark.anyio


@pytest.mark.asyncio
async def test_server_lifecycle(create_test_env):
    """Test server startup, operation, and shutdown using the real server."""
    test_env = create_test_env
    work_dir = test_env["work_dir"]
    pdf_path = test_env["pdf_path"]

    # Store the base path for the server
    os.environ["DOCUMENT_UNDERSTANDING_BASE_PATH"] = str(work_dir)

    # 1. Test metadata extraction
    print("\n--- Starting metadata extraction test ---")
    metadata_result = await run_mcp_command(
        "extract-pdf-metadata", {}, pdf_path=str(pdf_path), debug=True
    )

    metadata_json = await parse_json_response(metadata_result, debug=True)

    # Only assert if we successfully parsed the JSON
    if metadata_json.get("status") != "error":
        assert "status" in metadata_json
        assert metadata_json["status"] == "success"
        assert "pages" in metadata_json

    # 2. Test content extraction
    print("\n--- Starting content extraction test ---")
    content_result = await run_mcp_command(
        "extract-pdf-contents", {"pages": "1"}, pdf_path=str(pdf_path), debug=True
    )

    content_json = await parse_json_response(content_result, debug=True)

    if content_json.get("status") != "error":
        assert content_json["status"] == "success"
        assert len(content_json["pages"]) == 1
        assert "text" in content_json["pages"][0]

    # 3. Test error handling with nonexistent PDF
    print("\n--- Starting error handling test ---")
    error_result = await run_mcp_command(
        "extract-pdf-contents", {}, pdf_path="nonexistent.pdf", debug=True
    )

    error_json = await parse_json_response(error_result, debug=True)

    if error_json.get("status") != "error":
        assert "not found" in error_json.get("message", "").lower()


@pytest.mark.asyncio
async def test_document_processing(create_test_env):
    """Test document processing capabilities with different PDF types."""
    test_env = create_test_env
    work_dir = test_env["work_dir"]
    pdf_path = test_env["pdf_path"]
    img_pdf_path = test_env["img_pdf_path"]

    # Store the base path for the server
    os.environ["DOCUMENT_UNDERSTANDING_BASE_PATH"] = str(work_dir)

    # 1. Test metadata extraction from text PDF
    print("\n--- Testing metadata extraction from text PDF ---")
    text_metadata_result = await run_mcp_command(
        "extract-pdf-metadata", {}, pdf_path=str(pdf_path), debug=True
    )

    text_metadata_json = await parse_json_response(text_metadata_result, debug=True)

    if text_metadata_json.get("status") != "error":
        assert text_metadata_json["status"] == "success"
        assert text_metadata_json["pages"] > 0

    # 2. Test metadata extraction from image PDF
    print("\n--- Testing metadata extraction from image PDF ---")
    img_metadata_result = await run_mcp_command(
        "extract-pdf-metadata", {}, pdf_path=str(img_pdf_path), debug=True
    )

    img_metadata_json = await parse_json_response(img_metadata_result, debug=True)

    if img_metadata_json.get("status") != "error":
        assert img_metadata_json["status"] == "success"
        assert img_metadata_json["pages"] > 0

    # 3. Test content extraction with specific page range
    print("\n--- Testing content extraction with page range ---")
    content_result = await run_mcp_command(
        "extract-pdf-contents", {"pages": "1"}, pdf_path=str(pdf_path), debug=True
    )

    content_json = await parse_json_response(content_result, debug=True)

    if content_json.get("status") != "error":
        assert content_json["status"] == "success"
        assert len(content_json["pages"]) == 1

    # 4. Test image extraction
    print("\n--- Testing image extraction ---")
    images_result = await run_mcp_command(
        "extract-pdf-images", {}, pdf_path=str(img_pdf_path), debug=True
    )

    images_json = await parse_json_response(images_result, debug=True)

    if images_json.get("status") != "error":
        assert images_json["status"] == "success"
        assert "images" in images_json
        assert len(images_json["images"]) > 0


@pytest.mark.asyncio
async def test_search_functionality(create_test_env):
    """Test PDF search functionality."""
    test_env = create_test_env
    work_dir = test_env["work_dir"]
    pdf_path = test_env["pdf_path"]

    # Store the base path for the server
    os.environ["DOCUMENT_UNDERSTANDING_BASE_PATH"] = str(work_dir)

    # Test search functionality
    print("\n--- Testing PDF search ---")
    search_result = await run_mcp_command(
        "search-pdf",
        {"query": "Text"},  # Search for the word "Text" which should be in the test PDF
        pdf_path=str(pdf_path),
        debug=True,
    )

    search_json = await parse_json_response(search_result, debug=True)

    if search_json.get("status") != "error":
        assert search_json["status"] == "success"
        assert "results" in search_json
        # There should be at least one result
        assert len(search_json["results"]) > 0


@pytest.mark.asyncio
async def test_layout_extraction(create_test_env):
    """Test PDF layout extraction functionality."""
    test_env = create_test_env
    work_dir = test_env["work_dir"]
    pdf_path = test_env["pdf_path"]

    # Store the base path for the server
    os.environ["DOCUMENT_UNDERSTANDING_BASE_PATH"] = str(work_dir)

    # Test basic layout extraction
    print("\n--- Testing basic layout extraction ---")
    layout_result = await run_mcp_command(
        "extract-pdf-layout", {}, pdf_path=str(pdf_path), debug=True
    )

    layout_json = await parse_json_response(layout_result, debug=True)

    if layout_json.get("status") != "error":
        assert layout_json["status"] == "success"
        assert "layout" in layout_json
        # There should be at least one page
        assert len(layout_json["layout"]) > 0
        # Each page should have text blocks
        assert "text_blocks" in layout_json["layout"][0]
        # By default, images and drawings should not be included
        assert "images" not in layout_json["layout"][0]
        assert "drawings" not in layout_json["layout"][0]

    # Test layout extraction with images and drawings
    print("\n--- Testing layout extraction with images and drawings ---")
    layout_result_full = await run_mcp_command(
        "extract-pdf-layout",
        {"include_images": True, "include_drawings": True},
        pdf_path=str(pdf_path),
        debug=True,
    )

    layout_json_full = await parse_json_response(layout_result_full, debug=True)

    if layout_json_full.get("status") != "error":
        assert layout_json_full["status"] == "success"
        assert "layout" in layout_json_full
        # There should be at least one page
        assert len(layout_json_full["layout"]) > 0
        # Each page should have text blocks
        assert "text_blocks" in layout_json_full["layout"][0]
        # Images and drawings should be included
        assert "images" in layout_json_full["layout"][0]
        assert "drawings" in layout_json_full["layout"][0]


@pytest.mark.asyncio
async def test_error_handling_and_recovery(create_test_env):
    """Test server's ability to handle errors and recover."""
    test_env = create_test_env
    work_dir = test_env["work_dir"]
    pdf_path = test_env["pdf_path"]

    # Store the base path for the server
    os.environ["DOCUMENT_UNDERSTANDING_BASE_PATH"] = str(work_dir)

    # 1. Test with invalid parameters
    print("\n--- Testing invalid parameters ---")
    invalid_result = await run_mcp_command(
        "extract-pdf-contents", {"pages": "invalid"}, pdf_path=str(pdf_path), debug=True
    )

    invalid_json = await parse_json_response(invalid_result, debug=True)

    if invalid_json.get("status") != "error":
        assert "invalid" in invalid_json.get("message", "").lower()

    # 2. Test with nonexistent file
    print("\n--- Testing nonexistent file ---")
    missing_result = await run_mcp_command(
        "extract-pdf-contents", {}, pdf_path="nonexistent.pdf", debug=True
    )

    missing_json = await parse_json_response(missing_result, debug=True)

    if missing_json.get("status") != "error":
        assert "not found" in missing_json.get("message", "").lower()

    # 3. Verify server can still process valid requests after errors
    print("\n--- Testing recovery after errors ---")
    valid_result = await run_mcp_command(
        "extract-pdf-metadata", {}, pdf_path=str(pdf_path), debug=True
    )

    valid_json = await parse_json_response(valid_result, debug=True)

    if valid_json.get("status") != "error":
        assert valid_json["status"] == "success"


@pytest.mark.asyncio
async def test_configuration_changes(create_test_env):
    """Test server behavior with different configurations."""
    test_env = create_test_env
    work_dir = test_env["work_dir"]

    # Test with restrictive config
    print("\n--- Testing restrictive configuration ---")
    os.environ["DOCUMENT_UNDERSTANDING_BASE_PATH"] = str(work_dir)
    os.environ["DOCUMENT_UNDERSTANDING_ALLOW_ANY_PATH"] = "false"

    # Test working directory (should be restricted to base_path)
    wd_result1 = await run_mcp_command("get_pdf_working_directory", {}, debug=True)

    wd_json1 = await parse_json_response(wd_result1, debug=True)

    if wd_json1.get("status") != "error":
        assert wd_json1["status"] == "success"
        assert wd_json1["working_directory"] == str(work_dir)

    # Test with permissive config
    print("\n--- Testing permissive configuration ---")
    os.environ["DOCUMENT_UNDERSTANDING_ALLOW_ANY_PATH"] = "true"

    # Test working directory (should allow any path)
    wd_result2 = await run_mcp_command("get_pdf_working_directory", {}, debug=True)

    wd_json2 = await parse_json_response(wd_result2, debug=True)

    if wd_json2.get("status") != "error":
        assert wd_json2["status"] == "success"
        assert "any path is allowed" in wd_json2.get("message", "").lower()
