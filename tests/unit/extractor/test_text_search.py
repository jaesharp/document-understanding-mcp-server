import pytest
from unittest.mock import MagicMock, patch
from src.document_understanding.extractor import PDFExtractor  # Updated path
import fitz  # PyMuPDF
from src.document_understanding.exceptions import (
    PDFExtractionError,
    PDFPasswordError,
)  # Ensure imported

extractor_real = PDFExtractor()

# --- Tests for search_text --- #


def test_search_text_multi_page(mocker, test_pdfs_setup):
    """Test searching text across multiple pages, including missing text and errors."""
    extractor = PDFExtractor()
    pdf_path = str(test_pdfs_setup["all_elements"])  # Use a complex PDF

    # Mock document and page loading
    mock_doc = MagicMock(spec=fitz.Document)
    # Ensure page_count is an integer
    mock_doc.page_count = 3
    mock_doc.needs_pass = False  # Assume not password protected for this mock

    # Simulate different return values for search_for
    mock_page_0 = MagicMock(spec=fitz.Page)
    mock_page_0.search_for.return_value = [fitz.Rect(1, 1, 10, 10)]  # Found on page 1
    mock_page_2 = MagicMock(spec=fitz.Page)
    mock_page_2.search_for.return_value = [fitz.Rect(2, 2, 20, 20)]  # Found on page 3

    def load_page_side_effect(index):
        if index == 0:
            mock_page_0.number = 0  # Set number for consistency
            return mock_page_0
        if index == 2:
            mock_page_2.number = 2
            return mock_page_2
        # Simulate page 1 (index 1) not finding the text
        mock_page_1 = MagicMock(spec=fitz.Page)
        mock_page_1.number = 1
        mock_page_1.search_for.return_value = []
        return mock_page_1

    mock_doc.load_page.side_effect = load_page_side_effect

    # Mock the context manager returned by _open_pdf_document
    mock_doc_cm = MagicMock()
    mock_doc_cm.__enter__.return_value = mock_doc
    mock_doc_cm.__exit__.return_value = None
    mocker.patch.object(extractor, "_open_pdf_document", return_value=mock_doc_cm)

    # --- Test Valid Page Selection --- #
    results_valid = extractor.search_text(pdf_path, query="findme", pages_str="1, 3")
    assert len(results_valid) == 2
    assert results_valid[0]["page"] == 1
    assert results_valid[0]["rect"] == [1.0, 1.0, 10.0, 10.0]
    assert results_valid[1]["page"] == 3
    assert results_valid[1]["rect"] == [2.0, 2.0, 20.0, 20.0]
    # Ensure search_for was called correctly
    mock_page_0.search_for.assert_called_once_with("findme", quads=False)
    mock_page_2.search_for.assert_called_once_with("findme", quads=False)

    # --- Test Invalid Page Spec --- #
    invalid_spec = "1, bad-spec, 3"
    err_match_str = f"Failed to search PDF .* Invalid page number format: 'bad-spec'"
    # We need to reset the mock context manager for the error case
    mocker.patch.object(extractor, "_open_pdf_document", return_value=mock_doc_cm)
    with pytest.raises(PDFExtractionError, match=err_match_str):
        extractor.search_text(pdf_path, query="findme", pages_str=invalid_spec)


def test_search_text_empty_query(test_pdfs_setup):
    pdf_path = str(test_pdfs_setup["text"])
    with pytest.raises(ValueError, match="Search query cannot be empty"):
        extractor_real.search_text(pdf_path, "", None)


# File not found test for search_text
def test_search_text_file_not_found(mocker, test_pdfs_setup):
    """Tests FileNotFoundError for search_text."""
    pdf_path = str(test_pdfs_setup["non_existent"])
    extractor = PDFExtractor(file_exists_checker=MagicMock(return_value=False))
    with pytest.raises(FileNotFoundError):
        extractor.search_text(pdf_path, "query", None)


def test_search_text_invalid_page_spec(mocker, test_pdfs_setup):
    """Test search_text handles invalid page specifications correctly."""
    extractor = PDFExtractor()
    pdf_path = str(test_pdfs_setup["text"])  # Any multi-page PDF

    # Mock document opening
    mock_doc = MagicMock(spec=fitz.Document, page_count=3, needs_pass=False)
    mocker.patch.object(extractor, "_open_pdf_document", return_value=mock_doc)

    invalid_spec = "abc"
    # Update to expect PDFExtractionError and match the wrapped message
    err_match_str = f"Failed to search PDF .* Invalid page number format: 'abc'"
    with pytest.raises(PDFExtractionError, match=err_match_str):
        extractor.search_text(pdf_path, query="test", pages_str=invalid_spec)


# Test handling errors during page search
def test_search_text_page_error(mocker, test_pdfs_setup):
    """Test search_text handles errors during page searching loop."""
    extractor = PDFExtractor()
    pdf_path = str(test_pdfs_setup["text"])

    # Mock document setup
    mock_doc = MagicMock(spec=fitz.Document)
    mock_doc.page_count = 2
    mock_doc.needs_pass = False  # Set needs_pass to False

    mock_page0 = MagicMock(spec=fitz.Page)
    mock_page0.search_for.return_value = [fitz.Rect(0, 0, 1, 1)]  # Page 0 search OK
    mock_page1 = MagicMock(spec=fitz.Page)
    mock_page1.search_for.side_effect = Exception("Search Fail")  # Page 1 search fails
    mock_doc.load_page.side_effect = [mock_page0, mock_page1]

    # Mock the context manager returned by _open_pdf_document
    mock_doc_cm = MagicMock()
    mock_doc_cm.__enter__.return_value = mock_doc
    mock_doc_cm.__exit__.return_value = None
    mocker.patch.object(extractor, "_open_pdf_document", return_value=mock_doc_cm)
    # Ensure file exists check passes
    mocker.patch.object(extractor, "_file_exists", return_value=True)

    with patch.object(extractor, "log") as mock_logger:
        results = extractor.search_text(pdf_path, "test", "1,2")

    assert len(results) == 1  # Only result from page 0
    assert results[0]["page"] == 1
    mock_logger.warning.assert_called_once()  # Warning for page 1 failure
    assert "Failed to search page index 1" in mock_logger.warning.call_args[0][0]
    # Ensure the context manager and underlying doc mock were interacted with correctly
    extractor._open_pdf_document.assert_called_once_with(pdf_path, password=None)
    mock_doc_cm.__enter__.assert_called_once()
    assert mock_doc.load_page.call_count == 2
    mock_doc_cm.__exit__.assert_called_once()
