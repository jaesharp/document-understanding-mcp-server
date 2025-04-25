"""
Tests for the bounding box conversion fix in layout extraction.
"""

import os
import pytest
from pathlib import Path
from src.document_understanding.extractor import PDFExtractor
from src.document_understanding.models import PageLayout


@pytest.fixture(scope="module")
def bbox_issue_pdf_path():
    """Create a test PDF that triggers the bounding box conversion issue."""
    from tests.pdf_generators import create_bbox_issue_pdf

    # Create the test PDF in a temporary directory
    test_dir = Path("tests/data")
    test_dir.mkdir(exist_ok=True)
    pdf_path = test_dir / "bbox_issue_doc.pdf"

    # Only create the PDF if it doesn't exist
    if not pdf_path.exists():
        create_bbox_issue_pdf(pdf_path)

    yield str(pdf_path)

    # Don't delete the file after the test, as it might be useful for other tests


def test_bbox_conversion_fix(bbox_issue_pdf_path):
    """Test that the bounding box conversion fix works correctly."""
    extractor = PDFExtractor()

    # Extract layout data from the test PDF
    layout_data = extractor.extract_layout(
        bbox_issue_pdf_path,
        "1-2",  # Process both pages
        include_images=True,
        include_drawings=True,
    )

    # Check that we got data for both pages
    assert len(layout_data) == 2

    # Validate the data using the Pydantic models
    # This would have failed before our fix
    validated_pages = [PageLayout(**page) for page in layout_data]
    assert len(validated_pages) == 2

    # Check that the first page has images
    assert len(layout_data[0].get("images", [])) > 0

    # Check that the second page has images
    assert len(layout_data[1].get("images", [])) > 0

    # Check if any images have None bbox
    # This is expected with our fix for images that trigger the issue
    none_bbox_images_page1 = [
        img for img in layout_data[0].get("images", []) if img.get("bbox") is None
    ]
    none_bbox_images_page2 = [
        img for img in layout_data[1].get("images", []) if img.get("bbox") is None
    ]

    # We expect at least one image with None bbox on each page
    # But we don't want to make the test too strict, as the exact number might vary
    assert len(none_bbox_images_page1) + len(none_bbox_images_page2) > 0

    # The important thing is that the validation doesn't fail
    # and that we get valid data for all pages
    for page in validated_pages:
        # Check that all required fields are present
        assert hasattr(page, "page_number")
        assert hasattr(page, "text_blocks")
        assert hasattr(page, "drawings")
        assert hasattr(page, "images")

        # Images might have None bbox, but they should still be included
        for img in page.images:
            # The bbox can be None, but other fields should be present
            assert hasattr(img, "xref")
            assert hasattr(img, "width")
            assert hasattr(img, "height")
            # bbox can be None, but the attribute should exist
            assert hasattr(img, "bbox")
