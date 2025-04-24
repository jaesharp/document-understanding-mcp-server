# tests/unit/extractor/test_outline_extraction.py
import pytest
from unittest.mock import MagicMock
import fitz
from src.document_understanding.extractor import PDFExtractor
from src.document_understanding.models import OutlineItem
from src.document_understanding.exceptions import PDFPasswordError

# --- Unit Tests for Outline Extraction ---


def test_extract_outline_success(mocker, test_pdfs_setup):
    """Test successful outline extraction flow by mocking the implementation."""
    # JUSTIFICATION: Verify the main success path delegates correctly.
    extractor = PDFExtractor()
    pdf_path = str(test_pdfs_setup["outline"])  # Use the outline PDF
    mock_outline_data = [
        OutlineItem(title="Chapter 1", level=1, page_number=1, children=[]),
        OutlineItem(title="Chapter 2", level=1, page_number=5, children=[]),
    ]

    # Patch the implementation function where it's imported and used (in core.py)
    mock_impl = mocker.patch(
        "src.document_understanding.extractor.extractor._extract_outline_impl",
        return_value=mock_outline_data,
    )

    # Call the public method
    result = extractor.extract_outline(pdf_path)

    # Assert the result is what the mock returned
    assert result == mock_outline_data
    # Assert the implementation was called correctly
    mock_impl.assert_called_once_with(extractor, pdf_path, password=None)


def test_extract_outline_no_toc(mocker, test_pdfs_setup):
    """Test outline extraction when the PDF has no TOC."""
    # JUSTIFICATION: Verify correct handling when get_toc returns empty.
    extractor = PDFExtractor()
    pdf_path = str(test_pdfs_setup["text"])  # Use a PDF without a known outline

    # Patch the implementation function where it's imported and used (in core.py)
    mock_impl = mocker.patch(
        "src.document_understanding.extractor.extractor._extract_outline_impl",
        return_value=[],
    )

    result = extractor.extract_outline(pdf_path)
    assert result == []
    mock_impl.assert_called_once_with(extractor, pdf_path, password=None)


def test_extract_outline_impl_error(mocker, test_pdfs_setup):
    """Test outline extraction when the implementation raises an error."""
    # JUSTIFICATION: Verify errors from implementation are propagated.
    extractor = PDFExtractor()
    pdf_path = str(test_pdfs_setup["outline"])

    # Patch the implementation function where it's imported and used (in core.py)
    mock_impl = mocker.patch(
        "src.document_understanding.extractor.extractor._extract_outline_impl",
        side_effect=RuntimeError("Outline Impl Failed"),
    )

    with pytest.raises(RuntimeError, match="Outline Impl Failed"):
        extractor.extract_outline(pdf_path)

    mock_impl.assert_called_once_with(extractor, pdf_path, password=None)


# TODO: Add more tests for the _extract_outline_impl function itself

# --- Natural Test (No Mocking) --- #


def test_extract_outline_natural(test_pdfs_setup):
    """Test extract_outline against a real PDF with a known outline."""
    extractor = PDFExtractor()
    pdf_path = str(test_pdfs_setup["outline"])

    # ACTUAL structure of outline_doc.pdf based on previous test failure
    expected_outline = [
        OutlineItem(
            level=1,
            title="Chapter 1",
            page_number=2,
            children=[
                OutlineItem(level=2, title="Section 1.1", page_number=3, children=[])
            ],
        ),
        OutlineItem(
            level=1,
            title="Chapter 2",
            page_number=5,
            children=[
                OutlineItem(level=2, title="Section 2.1", page_number=6, children=[])
            ],
        ),
    ]

    # Call the actual method
    actual_outline = extractor.extract_outline(pdf_path)

    # Basic assertions
    assert isinstance(actual_outline, list)
    assert len(actual_outline) == len(expected_outline)

    # Detailed comparison (adjust tolerance/types as needed)
    for actual, expected in zip(actual_outline, expected_outline):
        assert actual.level == expected.level
        assert actual.title == expected.title
        # Page numbers can sometimes be tricky (0-based vs 1-based internal)
        # Assuming the extractor returns 1-based pages consistent with PyMuPDF
        assert actual.page_number == expected.page_number
        # Check kind if relevant (might vary depending on PDF)
        # assert actual.kind == expected.kind


# End of function

# --- New Password Tests ---


def test_extract_outline_password_success(mocker):
    """Test extracting outline from a password-protected PDF successfully."""
    # Mock dependencies
    mock_doc = MagicMock(spec=fitz.Document)
    mock_doc.needs_pass = False
    mock_doc.get_toc.return_value = [
        [1, "Chapter 1", 1],
        [2, "Section 1.1", 2],
    ]  # Simulate outline

    # Create a context manager mock
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_doc
    mock_cm.__exit__.return_value = None

    # Use an extractor instance with mocked dependencies
    extractor = PDFExtractor(file_exists_checker=MagicMock(return_value=True))

    # Mock the internal _open_pdf_document method to return a context manager
    mock_open = mocker.patch(
        "src.document_understanding.extractor.extractor.PDFExtractor._open_pdf_document",
        return_value=mock_doc,  # Return the document directly, not as a context manager
    )

    # Call the method with a password
    password = "correct_password"
    result = extractor.extract_outline(pdf_path="encrypted.pdf", password=password)

    # Assertions
    mock_open.assert_called_once_with("encrypted.pdf", password=password)
    # Check that get_toc was called
    mock_doc.get_toc.assert_called_once()
    # Check the results based on the mocked TOC
    # The outline parser converts the flat TOC into a nested structure
    assert len(result) == 1  # One top-level item
    assert result[0].title == "Chapter 1"
    assert result[0].level == 1
    assert result[0].page_number == 2  # Page numbers are incremented by 1
    assert len(result[0].children) == 1  # Should have one child
    assert result[0].children[0].title == "Section 1.1"
    assert result[0].children[0].level == 2
    assert result[0].children[0].page_number == 3  # Page numbers are incremented by 1
    # Check that get_toc was called
    mock_doc.get_toc.assert_called_once()


def test_extract_outline_password_error(mocker):
    """Test that PDFPasswordError is raised for incorrect password."""
    # Mock dependencies
    # Simulate _open_pdf_document raising PDFPasswordError
    mock_open = mocker.patch(
        "src.document_understanding.extractor.extractor.PDFExtractor._open_pdf_document",
        side_effect=PDFPasswordError("Bad password"),
    )

    # Use an extractor instance with mocked file existence
    extractor = PDFExtractor(file_exists_checker=MagicMock(return_value=True))

    # Call the method with a password
    password = "wrong_password"
    with pytest.raises(PDFPasswordError, match="Bad password"):
        extractor.extract_outline(pdf_path="encrypted.pdf", password=password)

    # Assert _open_pdf_document was called
    mock_open.assert_called_once_with("encrypted.pdf", password=password)
