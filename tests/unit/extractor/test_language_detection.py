# tests/unit/extractor/test_language_detection.py
import pytest
from unittest.mock import MagicMock
from langdetect import LangDetectException
from src.document_understanding.extractor import PDFExtractor
from src.document_understanding.exceptions import (
    PDFPasswordError,
)
from tests.conftest import test_pdfs_setup  # Import fixture reference

# --- Unit Tests for Language Detection ---


def test_detect_language_success(mocker, test_pdfs_setup):
    """Test successful language detection flow."""
    # JUSTIFICATION: Test the main success path including interaction with extract_content.
    extractor = PDFExtractor()
    pdf_path = str(test_pdfs_setup["text"])

    # Mock the underlying extract_content method called by the impl
    mock_content = [{"page_number": 1, "text": "Ceci est un test."}]
    mocker.patch.object(extractor, "extract_content", return_value=mock_content)

    # Mock the langdetect library function directly
    mock_detection = MagicMock(lang="fr", prob=0.99)
    mock_detect_langs = mocker.patch(
        "src.document_understanding.extractor.language_detection.detect_langs",
        return_value=[mock_detection],
    )

    result = extractor.detect_language(pdf_path, pages_str="1")

    assert "detections" in result
    assert len(result["detections"]) == 1
    assert result["detections"][0]["language_code"] == "fr"
    assert result["detections"][0]["confidence"] == 0.99
    assert result["text_sample_used"] == "Ceci est un test."

    # Verify mocks
    extractor.extract_content.assert_called_once_with(pdf_path, "1", password=None)
    mock_detect_langs.assert_called_once_with("Ceci est un test.")


def test_detect_language_extract_content_fails(mocker, test_pdfs_setup):
    """Test detect_language when the underlying extract_content fails."""
    # JUSTIFICATION: Test error handling when the dependency (extract_content) fails.
    extractor = PDFExtractor()
    pdf_path = str(test_pdfs_setup["text"])

    # Mock extract_content to raise an error
    mocker.patch.object(
        extractor, "extract_content", side_effect=ValueError("Content Extraction Error")
    )

    # Mock langdetect just in case, though it shouldn't be called
    mock_detect_langs = mocker.patch(
        "src.document_understanding.extractor.language_detection.detect_langs"
    )

    with pytest.raises(
        ValueError, match="Could not extract text sample.*Content Extraction Error"
    ):
        extractor.detect_language(pdf_path, pages_str="1")

    extractor.extract_content.assert_called_once_with(pdf_path, "1", password=None)
    mock_detect_langs.assert_not_called()


def test_detect_language_langdetect_fails(mocker, test_pdfs_setup):
    """Test detect_language when langdetect.detect_langs raises an error."""
    # JUSTIFICATION: Test error handling when the core detection library fails.
    extractor = PDFExtractor()
    pdf_path = str(test_pdfs_setup["text"])

    # Mock extract_content to succeed
    mock_content = [{"page_number": 1, "text": "Some text sample."}]
    mocker.patch.object(extractor, "extract_content", return_value=mock_content)

    # Mock langdetect to raise LangDetectException
    mock_detect_langs = mocker.patch(
        "src.document_understanding.extractor.language_detection.detect_langs",
        side_effect=LangDetectException(code=2, message="No features in text"),
    )

    with pytest.raises(
        ValueError, match="Could not reliably detect language.*No features in text"
    ):
        extractor.detect_language(pdf_path, pages_str="1")

    extractor.extract_content.assert_called_once_with(pdf_path, "1", password=None)
    mock_detect_langs.assert_called_once_with("Some text sample.")


# Update test_empty_pdf_cases_detect_language to test the specific ValueError
def test_empty_pdf_cases_detect_language(test_pdfs_setup):
    """Test detect_language on empty PDF expects ValueError."""
    # JUSTIFICATION: Test the specific error raised when no text can be extracted from an empty/invalid PDF.
    extractor_real = PDFExtractor()
    pdf_path = str(test_pdfs_setup["empty"])
    # The error comes from parse_pages or extract_content failing first.
    # Let's test the expected outcome, which is a ValueError wrapping the underlying issue.
    # The exact message might depend on whether parse_pages or extract_content raises first.
    # We expect a ValueError indicating failure to get a sample.
    with pytest.raises(
        ValueError, match=r"Could not extract text sample|No text content found"
    ):
        extractor_real.detect_language(pdf_path, pages_str=None)


# TODO: Add more tests for the _detect_language_impl function itself

# --- New Password Tests ---


def test_detect_language_password_success(mocker):
    """Test language detection on a password-protected PDF successfully."""
    # Mock dependencies
    extractor = PDFExtractor(file_exists_checker=MagicMock(return_value=True))

    # Mock the extract_content method called by the impl
    mock_extract_content = mocker.patch.object(
        extractor,
        "extract_content",
        return_value=[{"text": "This is a sample text in English."}],
    )

    # Mock the actual langdetect function (to avoid real detection)
    mock_detect_langs = mocker.patch(
        "src.document_understanding.extractor.language_detection.detect_langs",
        return_value=[mocker.Mock(lang="en", prob=0.99)],
    )

    # Call the method with a password
    password = "correct_pass"
    result = extractor.detect_language(
        "encrypted.pdf", pages_str="1", password=password
    )

    # Assertions
    mock_extract_content.assert_called_once_with(
        "encrypted.pdf", "1", password=password
    )
    mock_detect_langs.assert_called_once_with("This is a sample text in English.")
    assert result["detections"][0]["language_code"] == "en"


def test_detect_language_password_error(mocker):
    """Test that PDFPasswordError from extract_content is handled."""
    # Mock dependencies
    extractor = PDFExtractor(file_exists_checker=MagicMock(return_value=True))

    # Mock extract_content to raise PDFPasswordError
    mock_extract_content = mocker.patch.object(
        extractor,
        "extract_content",
        side_effect=PDFPasswordError("Incorrect password for text extraction"),
    )

    # Call the method with a password
    password = "wrong_pass"
    with pytest.raises(
        PDFPasswordError, match="Incorrect password for text extraction"
    ):
        extractor.detect_language("encrypted.pdf", pages_str="1", password=password)

    # Assert extract_content was called
    mock_extract_content.assert_called_once_with(
        "encrypted.pdf", "1", password=password
    )
