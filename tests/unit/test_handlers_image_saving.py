"""Unit tests for the extract_images handler with output_directory parameter."""

import pytest
from unittest.mock import MagicMock, patch
from document_understanding.handlers import handle_extract_images


def test_handle_extract_images_with_output_directory(mocker):
    """Test the extract_images handler with output_directory parameter."""
    # Mock the extractor
    mock_extractor = MagicMock()
    mock_extractor.extract_images.return_value = [
        {
            "page_number": 1,
            "xref": 1,
            "width": 100,
            "height": 100,
            "file_path": "/tmp/image.png",
        }
    ]
    mocker.patch(
        "document_understanding.handlers.get_extractor", return_value=mock_extractor
    )

    # Call the handler
    result = handle_extract_images(
        {
            "include_data": True,
            "min_width": 10,
            "min_height": 10,
            "output_directory": "/tmp/images",
        },
        "test.pdf",
        "1",
    )

    # Verify the extractor was called with correct parameters
    mock_extractor.extract_images.assert_called_once_with(
        pdf_path="test.pdf",
        pages_str="1",
        include_data=True,
        min_width=10,
        min_height=10,
        filter_bbox=None,
        output_directory="/tmp/images",
        save_without_returning_data=False,
    )

    # Verify the result
    assert result.status == "success"
    assert len(result.data.images) == 1
    assert result.data.images[0].file_path == "/tmp/image.png"
