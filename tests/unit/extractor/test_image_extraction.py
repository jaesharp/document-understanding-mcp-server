import pytest
from unittest.mock import MagicMock, patch
from src.document_understanding.extractor import PDFExtractor
from src.document_understanding.exceptions import PDFExtractionError, PDFPasswordError
import fitz
import logging  # Added logging
import base64  # Added for filtering test

# Use a single real instance for tests needing it
extractor_real = PDFExtractor()

# --- Tests for extract_images --- #


def test_extract_images_bbox_mismatch(pdf_extractor_instance, mocker):
    """Test handling get_image_rects returning fewer items than get_images."""
    extractor = pdf_extractor_instance
    mock_doc = extractor._mock_doc
    mock_doc.needs_pass = False
    mock_page = MagicMock(spec=fitz.Page)
    mock_page.get_images.return_value = [(123, 0, 100, 100, 8, "DeviceRGB")]
    mock_page.get_image_rects.return_value = []  # Return empty list
    mock_doc.page_count = 1
    mock_doc.load_page.return_value = mock_page
    images = extractor.extract_images("dummy.pdf", "1")
    assert len(images) == 1  # Expect one result even if bbox fails
    assert images[0].get("bbox") is None  # Assert bbox is missing


def test_extract_images_invalid_bbox_type(mocker):
    """Test that invalid bbox type is logged and skipped.
    UPDATE: Logic changed - image is no longer skipped, bbox is just omitted.
    """
    # Mock the page and image info
    mock_page = MagicMock()
    # Return an image info tuple with a valid xref but invalid bbox
    mock_page.get_images.return_value = [(1, 0, 50, 50)]
    # Mock get_image_rects to return a string instead of a Rect object
    mock_page.get_image_rects.return_value = ["invalid_bbox_string"]
    mock_doc = MagicMock()
    mock_doc.page_count = 1
    mock_doc.load_page.return_value = mock_page
    mock_doc.needs_pass = False

    # Mock the PDF opener to return the mock_doc directly
    extractor = PDFExtractor(capabilities={"tesseract_ocr": False})
    mocker.patch.object(extractor, "_open_pdf", return_value=mock_doc)
    mocker.patch.object(extractor, "_file_exists", return_value=True)

    # Run the extraction
    results = extractor.extract_images("dummy.pdf", pages_str="1", include_data=False)

    # Assertions
    assert len(results) == 1  # Expect 1 result now
    assert "bbox" not in results[0]  # Assert bbox is missing
    assert results[0]["xref"] == 1  # Check xref


def test_extract_images_empty_image_data(pdf_extractor_instance, mocker):
    """Test handling when doc.extract_image returns empty bytes."""
    extractor = pdf_extractor_instance
    mock_doc = extractor._mock_doc
    mock_doc.needs_pass = False
    mock_page = MagicMock(spec=fitz.Page)
    mock_page.get_images.return_value = [(123, 0, 100, 100, 8, "DeviceRGB")]
    mock_page.get_image_rects.return_value = [fitz.Rect(0, 0, 100, 100)]
    mock_doc.page_count = 1
    mock_doc.load_page.return_value = mock_page
    mock_doc.extract_image.return_value = {"image": b"", "ext": "png"}
    images = extractor.extract_images("dummy.pdf", "1", include_data=True)
    assert len(images) == 1
    assert images[0]["xref"] == 123
    assert "data" in images[0]
    assert images[0]["data"] == ""
    assert "format" in images[0]
    assert images[0]["format"] == "png"
    mock_doc.extract_image.assert_called_once_with(123)


def test_extract_images_multi_page(mocker, test_pdfs_setup):
    """Test extracting images across multiple specified pages, including error case."""
    extractor = PDFExtractor()
    pdf_path = str(
        test_pdfs_setup["all_elements"]
    )  # Use PDF with images on multiple pages

    # Mock _open_pdf_document to return a mock with page_count
    mock_doc = MagicMock(spec=fitz.Document, page_count=3, needs_pass=False)
    # Simulate load_page returning mock pages with image lists
    mock_page_0 = MagicMock(spec=fitz.Page)
    mock_page_0.get_images.return_value = [(1, 0, 10, 10)]  # Image on page 1
    mock_page_0.get_image_rects.return_value = [fitz.Rect(1, 1, 11, 11)]
    mock_page_2 = MagicMock(spec=fitz.Page)
    mock_page_2.get_images.return_value = [(2, 0, 20, 20)]  # Image on page 3
    mock_page_2.get_image_rects.return_value = [fitz.Rect(2, 2, 22, 22)]

    def load_page_side_effect(index):
        if index == 0:
            return mock_page_0
        if index == 2:
            return mock_page_2
        # Simulate page 1 (index 1) having no images
        mock_page_1 = MagicMock(spec=fitz.Page)
        mock_page_1.get_images.return_value = []
        return mock_page_1

    mock_doc.load_page.side_effect = load_page_side_effect
    mocker.patch.object(extractor, "_open_pdf_document", return_value=mock_doc)

    # --- Test Valid Page Selection --- #
    results_valid = extractor.extract_images(pdf_path, pages_str="1, 3")
    assert len(results_valid) == 2
    assert results_valid[0]["page_number"] == 1
    assert results_valid[0]["xref"] == 1
    assert results_valid[1]["page_number"] == 3
    assert results_valid[1]["xref"] == 2

    # --- Test Invalid Page Spec --- #
    # Update to expect PDFExtractionError and match the wrapped message
    invalid_spec = "1, invalid-page"
    err_match_str = "Failed to process image extraction for PDF .* Invalid page number format: 'invalid-page'"
    with pytest.raises(PDFExtractionError, match=err_match_str):
        extractor.extract_images(pdf_path, pages_str=invalid_spec)


def test_extract_images_data_extraction_error(pdf_extractor_instance, mocker):
    """Test extract_images handles errors during data extraction."""
    extractor = pdf_extractor_instance
    mock_doc = extractor._mock_doc
    mock_doc.needs_pass = False
    mock_page = MagicMock(spec=fitz.Page)
    mock_page.get_images.return_value = [(123, 0, 100, 100, 8, "DeviceRGB")]
    mock_page.get_image_rects.return_value = [fitz.Rect(10, 10, 110, 110)]
    mock_doc.page_count = 1
    mock_doc.load_page.return_value = mock_page
    mock_doc.extract_image.side_effect = Exception("Cannot extract image data")

    # Patch the log object on the instance
    with patch.object(extractor, "log") as mock_logger:
        images = extractor.extract_images("dummy.pdf", "1", include_data=True)

    assert len(images) == 1  # Should still get the image description
    assert images[0]["xref"] == 123
    assert "data" not in images[0]  # Data extraction failed
    assert "format" not in images[0]

    # Assert the warning method was called on the mocked logger
    mock_logger.warning.assert_called_once()
    # Optionally, check call args (might be brittle with structlog formatting)
    # call_args, call_kwargs = mock_logger.warning.call_args
    # assert "Failed to extract image data" in call_args[0]
    # assert call_kwargs.get('xref') == 123
    # assert "Cannot extract image data" in call_kwargs.get('error')


def test_extract_images_page_error(pdf_extractor_instance, mocker):
    """Test extract_images handles errors during page processing."""
    extractor = pdf_extractor_instance
    mock_doc = extractor._mock_doc
    mock_doc.needs_pass = False
    mock_page = MagicMock(spec=fitz.Page)
    mock_page.get_images.side_effect = Exception("Cannot get images")
    mock_doc.page_count = 1
    mock_doc.load_page.return_value = mock_page

    # Patch the correct logger attribute name
    with patch.object(extractor, "log") as mock_logger:
        images = extractor.extract_images("dummy.pdf", "1")

    assert images == []  # Expect empty results if page processing fails
    mock_logger.warning.assert_called_once()


def test_extract_images_integration(test_pdfs_setup):
    """Integration test for extract_images using real image PDF.
    This PDF contains a Form XObject. The test expects partial info
    to be returned even though getting the bbox might fail."""
    pdf_path = str(test_pdfs_setup["image"])
    images = extractor_real.extract_images(pdf_path, pages_str="1")
    assert len(images) == 1
    image_info = images[0]
    assert image_info["page_number"] == 1
    # The xref might vary between different versions of PyMuPDF/fitz,
    # so we'll just verify it exists rather than check exact value
    assert "xref" in image_info
    assert isinstance(image_info["xref"], int)
    assert image_info["width"] > 0
    assert image_info["height"] > 0
    # The bbox might be None or present depending on how the image was embedded
    # We'll just check the structure without asserting its presence/absence


# File not found test for extract_images
def test_extract_images_file_not_found(mocker, test_pdfs_setup):
    """Tests FileNotFoundError for extract_images."""
    pdf_path = str(test_pdfs_setup["non_existent"])
    extractor = PDFExtractor(file_exists_checker=MagicMock(return_value=False))
    with pytest.raises(FileNotFoundError):
        extractor.extract_images(pdf_path, None)


# Invalid page spec test for extract_images
def test_extract_images_invalid_page_spec(pdf_extractor_instance, test_pdfs_setup):
    """Tests error for invalid page spec for extract_images."""
    pdf_path = str(test_pdfs_setup["text"])
    invalid_spec = "1, abc"
    err_match = "Invalid page number format: 'abc'"
    pdf_extractor_instance._mock_doc.page_count = 10  # Set page count
    pdf_extractor_instance._mock_doc.needs_pass = False
    # Expect PDFExtractionError wrapping the original ValueError
    with pytest.raises(PDFExtractionError, match=err_match):
        pdf_extractor_instance.extract_images(pdf_path, invalid_spec)


def test_extract_images_filtering(mocker):
    """Test extract_images filtering by min_width, min_height, and region."""
    # Justification: Test the core filtering logic added to extract_images.

    # -- Mock PDF Setup --
    mock_page = MagicMock(spec=fitz.Page)
    mock_doc = MagicMock(spec=fitz.Document)
    mock_doc.page_count = 1
    mock_doc.load_page.return_value = mock_page
    mock_doc.needs_pass = False

    # Mock _open_pdf to return the mock_doc directly, not a context manager
    mock_pdf_opener = MagicMock(return_value=mock_doc)
    mock_file_exists = MagicMock(return_value=True)

    # -- Mock Image Data --
    # Image 1: Small (50x50) inside region (100,100,200,200)
    img_info1 = (1, 0, 50, 50)  # xref, smask, w, h
    bbox1 = fitz.Rect(100, 100, 150, 150)
    # Image 2: Large (300x300) inside region (100,100,450,450)
    img_info2 = (2, 0, 300, 300)
    bbox2 = fitz.Rect(120, 120, 420, 420)
    # Image 3: Medium (150x150) outside region (0,0,50,50)
    img_info3 = (3, 0, 150, 150)
    bbox3 = fitz.Rect(0, 0, 150, 150)
    # Image 4: Tall (50x200) touching region (0,0,100,100)
    img_info4 = (4, 0, 50, 200)
    bbox4 = fitz.Rect(25, 0, 75, 200)  # Touches (0,0,100,100) but not fully inside
    # Image 5: No bbox available
    img_info5 = (5, 0, 100, 100)

    mock_page.get_images.return_value = [
        img_info1,
        img_info2,
        img_info3,
        img_info4,
        img_info5,
    ]
    # Return bboxes in order, simulate one failure (for img_info5)
    mock_page.get_image_rects.return_value = [bbox1, bbox2, bbox3, bbox4, None]

    # -- Extractor Instance --
    # Use mocked dependencies, similar to pdf_extractor_instance fixture
    extractor = PDFExtractor(
        file_exists_checker=mock_file_exists, pdf_opener=mock_pdf_opener
    )

    # -- Test Cases --
    test_cases = [
        # Case 1: No filters. Image 5 (no bbox) should now be included.
        ({}, [1, 2, 3, 4, 5]),  # Added 5
        # Case 2: Filter by min_width=100 - excludes 1, 4 (size). Includes 5 (size 100x100).
        ({"min_width": 100}, [2, 3, 5]),
        # Case 3: Filter by min_height=200 - excludes 1, 3, 5 (size). Includes 4.
        ({"min_height": 200}, [2, 4]),
        # Case 4: Filter by min_width=100 AND min_height=200 - excludes 1, 3, 4, 5 (size).
        ({"min_width": 100, "min_height": 200}, [2]),
        # Case 5: Filter by region [100, 100, 450, 450] - passes [1, 2]. Excludes 3, 4 (region). Excludes 5 (no bbox).
        ({"filter_bbox": [100, 100, 450, 450]}, [1, 2]),
        # Case 6: Filter by region [110, 110, 140, 140] (contains none) - excludes 1, 2, 3, 4 (region). Excludes 5 (no bbox).
        ({"filter_bbox": [110, 110, 140, 140]}, []),
        # Case 7: Filter by region [0, 0, 50, 50] (contains none) - excludes 1, 2, 3, 4 (region). Excludes 5 (no bbox).
        ({"filter_bbox": [0, 0, 50, 50]}, []),
        # Case 8: Region [100,100,450,450] passes [1, 2]. Min_width=100/min_height=100 excludes 1 (size). Excludes 5 (no bbox).
        (
            {"filter_bbox": [100, 100, 450, 450], "min_width": 100, "min_height": 100},
            [2],
        ),
        # Case 9: include_data=True (no filters). Includes 5.
        ({"include_data": True}, [1, 2, 3, 4, 5]),  # Added 5
        # Case 10: Filter by min_width=100 AND min_height=150 - excludes 1, 4 (size), 5 (height). Includes 2, 3.
        ({"min_width": 100, "min_height": 150}, [2, 3]),  # Corrected: Removed 5
        # Case 11: Filter by region [50, 50, 160, 160] (contains 1) - excludes 2, 3, 4 (region). Excludes 5 (no bbox).
        ({"filter_bbox": [50, 50, 160, 160]}, [1]),
        # Case 12: Filter by region [40, 40, 270, 180] (contains 1) - excludes 2, 3, 4 (region). Excludes 5 (no bbox).
        ({"filter_bbox": [40, 40, 270, 180]}, [1]),
    ]

    # Mock extract_image for data tests
    def mock_extract_image(xref):
        if xref in [1, 2, 3, 4]:  # Only mock for images with bboxes
            return {"image": f"data_for_{xref}".encode("utf-8"), "ext": "png"}
        else:
            raise Exception("Cannot extract image")

    mock_doc.extract_image.side_effect = mock_extract_image

    for filters, expected_xrefs in test_cases:
        print(f"Running test with filters: {filters}")
        result = extractor.extract_images("dummy.pdf", pages_str="1", **filters)

        # Verify the number of results
        assert len(result) == len(expected_xrefs), f"Filters: {filters}"

        # Verify the correct xrefs are present
        actual_xrefs = [img["xref"] for img in result]
        assert sorted(actual_xrefs) == sorted(expected_xrefs), f"Filters: {filters}"

        # Verify bbox presence/absence
        for img in result:
            if img["xref"] == 5:
                assert (
                    "bbox" not in img
                ), f"Filters: {filters}, Image 5 should not have bbox"
            else:
                assert (
                    "bbox" in img
                ), f"Filters: {filters}, Image {img['xref']} should have bbox"

        # Verify data presence if requested
        if filters.get("include_data"):
            for img in result:
                if img["xref"] in [1, 2, 3, 4]:  # Only images we mocked data for
                    assert (
                        "data" in img
                    ), f"Filters: {filters}, Image {img['xref']} missing data"
                    assert img["data"] == base64.b64encode(
                        f"data_for_{img['xref']}".encode("utf-8")
                    ).decode("utf-8")
                    assert img["format"] == "png"
                else:
                    assert (
                        "data" not in img
                    ), f"Filters: {filters}, Image {img['xref']} should not have data"


# --- New Password Tests ---


def test_extract_images_password_success(mocker):
    """Test extracting images from a password-protected PDF successfully."""
    # Mock dependencies
    mock_doc = MagicMock(spec=fitz.Document)
    mock_doc.page_count = 1
    mock_page = MagicMock(spec=fitz.Page)
    mock_page.get_images.return_value = [(1, 0, 50, 50)]  # Dummy image
    mock_page.get_image_rects.return_value = [fitz.Rect(0, 0, 50, 50)]  # Dummy bbox
    mock_doc.load_page.return_value = mock_page
    mock_doc.needs_pass = False  # Assume password worked

    # Use an extractor instance with mocked dependencies
    extractor = PDFExtractor(file_exists_checker=MagicMock(return_value=True))

    # Mock the internal _open_pdf_document method - THIS IS SUFFICIENT
    mock_open = mocker.patch.object(
        extractor, "_open_pdf_document", return_value=mock_doc
    )

    # Call the method with a password
    password = "correct_password"
    result = extractor.extract_images("encrypted.pdf", pages_str="1", password=password)

    # Assertions
    mock_open.assert_called_once_with("encrypted.pdf", password=password)
    assert len(result) == 1  # Check result from mocked page processing
    assert result[0]["xref"] == 1
    # The doc.close() call is now handled inside the implementation, so we don't assert it here


def test_extract_images_password_error(mocker):
    """Test that PDFPasswordError is raised for incorrect password."""
    # Mock dependencies
    # Simulate _open_pdf_document raising PDFPasswordError
    mock_open = mocker.patch(
        "src.document_understanding.extractor.extractor.PDFExtractor._open_pdf_document",
        side_effect=PDFPasswordError("Incorrect password"),
    )

    # Use an extractor instance with mocked file existence
    extractor = PDFExtractor(file_exists_checker=MagicMock(return_value=True))

    # Call the method with a password
    password = "wrong_password"
    with pytest.raises(PDFPasswordError, match="Incorrect password"):
        extractor.extract_images("encrypted.pdf", pages_str="1", password=password)

    # Assert _open_pdf_document was called
    mock_open.assert_called_once_with("encrypted.pdf", password=password)
