# Tests for implementation functions in content_extraction.py

"""Tests for the internal implementation functions in content_extraction.py."""

from unittest.mock import MagicMock, patch, ANY, call  # Import call
import fitz  # For spec
from PIL import Image  # Needed for mocks
import io  # Needed for mocks

# Function to test
from src.document_understanding.extractor.content_extraction import (
    _extract_page_text_impl,
)

# Attempt to import TesseractError for realistic testing
TesseractError = None
try:
    from pytesseract import TesseractError as RealTesseractError

    TesseractError = RealTesseractError
except ImportError:
    # If pytesseract isn't installed in test env, create a dummy exception
    class DummyTesseractError(Exception):
        def __init__(self, status=1, message="Dummy Tesseract Error"):
            super().__init__(f"({status}, '{message}')")
            self.status = status
            self.message = message

    TesseractError = DummyTesseractError
    print(
        "\n[INFO] pytesseract not found, using dummy TesseractError for testing _extract_page_text_impl"
    )

# --- Helper to create mock extractor instance ---


def create_mock_extractor(mocker, ocr_enabled=False, ocr_runner=None):
    """Creates a mock object mimicking PDFExtractor for _extract_page_text_impl."""
    mock_extractor = MagicMock()
    mock_extractor.logger = MagicMock()
    mock_extractor.ocr_enabled = ocr_enabled
    mock_extractor._ocr_runner = ocr_runner
    return mock_extractor


# --- Tests for _extract_page_text_impl --- #


def test_impl_extract_page_text_direct_success(mocker):
    """Test successful direct text extraction path."""
    mock_page = MagicMock(spec=fitz.Page, number=0)
    mock_page.get_text.return_value = " Direct Text "
    mock_extractor = create_mock_extractor(mocker, ocr_enabled=False)

    result = _extract_page_text_impl(mock_extractor, mock_page, ocr_language="eng")

    assert result == "Direct Text"
    mock_page.get_text.assert_called_once_with("text")
    mock_extractor.logger.debug.assert_called()


def test_impl_extract_page_text_get_text_error_no_ocr(mocker):
    """Test error during get_text when OCR is disabled."""
    mock_page = MagicMock(spec=fitz.Page, number=0)
    mock_page.get_text.side_effect = Exception("GetText Failed")
    mock_extractor = create_mock_extractor(mocker, ocr_enabled=False)

    result = _extract_page_text_impl(mock_extractor, mock_page, ocr_language="eng")

    assert result == ""
    mock_extractor.logger.warning.assert_called_once()
    args, kwargs = mock_extractor.logger.warning.call_args
    assert "Direct text extraction failed" in args[0]
    assert kwargs.get("error") == "GetText Failed"
    mock_extractor.logger.debug.assert_called_once()  # Debug log for 'OCR not enabled' path


def test_impl_extract_page_text_fallback_ocr_success(mocker):
    """Test successful OCR fallback when get_text fails."""
    mock_page = MagicMock(spec=fitz.Page, number=1)
    mock_page.get_text.side_effect = Exception("GetText Failed")
    mock_pixmap = MagicMock()
    mock_pixmap.tobytes.return_value = b"imgdata"
    mock_page.get_pixmap.return_value = mock_pixmap

    mock_ocr_runner = MagicMock(return_value=" OCR Text ")
    mock_extractor = create_mock_extractor(
        mocker, ocr_enabled=True, ocr_runner=mock_ocr_runner
    )

    with patch(
        "src.document_understanding.extractor.content_extraction.Image.open"
    ) as mock_image_open:
        result = _extract_page_text_impl(mock_extractor, mock_page, ocr_language="eng")

    assert result == "OCR Text"
    mock_page.get_text.assert_called_once_with("text")
    mock_page.get_pixmap.assert_called_once_with(dpi=300)
    mock_image_open.assert_called_once()
    mock_ocr_runner.assert_called_once_with(ANY, "eng")
    assert mock_extractor.logger.warning.call_count == 1  # Direct fail
    assert mock_extractor.logger.debug.call_count == 2  # Fallback path + Success


def test_impl_extract_page_text_fallback_ocr_failure(mocker):
    """Test OCR failure during fallback."""
    mock_page = MagicMock(spec=fitz.Page, number=2)
    mock_page.get_text.side_effect = Exception("GetText Failed")
    mock_pixmap = MagicMock()
    mock_pixmap.tobytes.return_value = b"imgdata"
    mock_page.get_pixmap.return_value = mock_pixmap

    mock_ocr_runner = MagicMock(side_effect=Exception("OCR Process Failed"))
    mock_extractor = create_mock_extractor(
        mocker, ocr_enabled=True, ocr_runner=mock_ocr_runner
    )

    with patch(
        "src.document_understanding.extractor.content_extraction.Image.open"
    ) as mock_image_open:
        result = _extract_page_text_impl(mock_extractor, mock_page, ocr_language="eng")

    assert result == "[OCR failed: OCR Process Failed]"
    mock_ocr_runner.assert_called_once()
    assert mock_extractor.logger.warning.call_count == 1  # Direct fail
    assert mock_extractor.logger.error.call_count == 1  # OCR fail
    args, kwargs = mock_extractor.logger.error.call_args
    assert "OCR fallback failed (generic error)" in args[0]
    assert "OCR Process Failed" in kwargs.get("error")


def test_impl_extract_page_text_fallback_tesseract_error(mocker):
    """Test specific TesseractError during fallback."""
    mock_page = MagicMock(spec=fitz.Page, number=3)
    mock_page.get_text.side_effect = Exception("GetText Failed")
    mock_pixmap = MagicMock()
    mock_pixmap.tobytes.return_value = b"imgdata"
    mock_page.get_pixmap.return_value = mock_pixmap

    tesseract_error_instance = TesseractError(status=1, message="Fake Tesseract Error")
    mock_ocr_runner = MagicMock(side_effect=tesseract_error_instance)
    mock_extractor = create_mock_extractor(
        mocker, ocr_enabled=True, ocr_runner=mock_ocr_runner
    )

    with patch(
        "src.document_understanding.extractor.content_extraction.Image.open"
    ) as mock_image_open:
        result = _extract_page_text_impl(mock_extractor, mock_page, ocr_language="deu")

    assert f"[OCR failed: {tesseract_error_instance}]" in result
    assert mock_extractor.logger.warning.call_count == 1  # Direct fail
    assert mock_extractor.logger.error.call_count == 1  # OCR fail
    args, kwargs = mock_extractor.logger.error.call_args
    assert "OCR fallback failed (TesseractError)" in args[0]
    assert kwargs.get("ocr_language") == "deu"


def test_impl_extract_page_text_force_ocr_success(mocker):
    """Test successful forced OCR."""
    mock_page = MagicMock(spec=fitz.Page, number=4)
    mock_pixmap = MagicMock()
    mock_pixmap.tobytes.return_value = b"imgdata"
    mock_page.get_pixmap.return_value = mock_pixmap

    mock_ocr_runner = MagicMock(return_value=" Forced OCR OK ")
    mock_extractor = create_mock_extractor(
        mocker, ocr_enabled=True, ocr_runner=mock_ocr_runner
    )

    with patch(
        "src.document_understanding.extractor.content_extraction.Image.open"
    ) as mock_image_open:
        result = _extract_page_text_impl(
            mock_extractor, mock_page, ocr_language="eng", force_ocr=True
        )

    assert result == "Forced OCR OK"
    mock_page.get_text.assert_not_called()
    mock_page.get_pixmap.assert_called_once_with(dpi=300)
    mock_ocr_runner.assert_called_once()
    assert mock_extractor.logger.debug.call_count == 2  # Forced path + Success


def test_impl_extract_page_text_force_ocr_disabled(mocker):
    """Test forced OCR when OCR is disabled."""
    mock_page = MagicMock(spec=fitz.Page, number=5)
    mock_extractor = create_mock_extractor(mocker, ocr_enabled=False)

    result = _extract_page_text_impl(
        mock_extractor, mock_page, ocr_language="eng", force_ocr=True
    )

    assert result == "[OCR forced but unavailable]"
    mock_page.get_text.assert_not_called()
    mock_page.get_pixmap.assert_not_called()
    mock_extractor.logger.warning.assert_called_once_with(
        "OCR forced but unavailable (not enabled or configured).", page_number=5
    )


def test_impl_extract_page_text_force_ocr_runner_none(mocker):
    """Test forced OCR when runner is None (internal error state)."""
    mock_page = MagicMock(spec=fitz.Page, number=6)
    # Simulate OCR enabled but runner missing
    mock_extractor = create_mock_extractor(mocker, ocr_enabled=True, ocr_runner=None)

    result = _extract_page_text_impl(
        mock_extractor, mock_page, ocr_language="eng", force_ocr=True
    )

    assert result == "[OCR failed: Runner not available]"
    mock_extractor.logger.error.assert_called_once_with(
        "OCR forced but runner is None (internal error).", page_number=6
    )


def test_impl_extract_page_text_force_ocr_pixmap_fail(mocker):
    """Test forced OCR failure during pixmap generation."""
    mock_page = MagicMock(spec=fitz.Page, number=7)
    mock_page.get_pixmap.return_value.tobytes.return_value = b""  # Empty bytes

    mock_ocr_runner = MagicMock()
    mock_extractor = create_mock_extractor(
        mocker, ocr_enabled=True, ocr_runner=mock_ocr_runner
    )

    with patch(
        "src.document_understanding.extractor.content_extraction.Image.open"
    ) as mock_image_open:
        result = _extract_page_text_impl(
            mock_extractor, mock_page, ocr_language="eng", force_ocr=True
        )

    assert result == "[OCR failed: Pixmap empty]"
    mock_page.get_pixmap.assert_called_once()
    mock_ocr_runner.assert_not_called()
    mock_extractor.logger.warning.assert_called_once_with(
        "Pixmap generation resulted in empty bytes for OCR", page_number=7
    )


def test_impl_extract_page_text_force_ocr_tesseract_error(mocker):
    """Test specific TesseractError during forced OCR."""
    mock_page = MagicMock(spec=fitz.Page, number=8)
    mock_pixmap = MagicMock()
    mock_pixmap.tobytes.return_value = b"imgdata"
    mock_page.get_pixmap.return_value = mock_pixmap

    tesseract_error_instance = TesseractError(
        status=2, message="Forced Tesseract Error"
    )
    mock_ocr_runner = MagicMock(side_effect=tesseract_error_instance)
    mock_extractor = create_mock_extractor(
        mocker, ocr_enabled=True, ocr_runner=mock_ocr_runner
    )

    with patch(
        "src.document_understanding.extractor.content_extraction.Image.open"
    ) as mock_image_open:
        result = _extract_page_text_impl(
            mock_extractor, mock_page, ocr_language="fra", force_ocr=True
        )

    assert f"[OCR failed: {tesseract_error_instance}]" in result
    mock_ocr_runner.assert_called_once()
    assert mock_extractor.logger.error.call_count == 1
    args, kwargs = mock_extractor.logger.error.call_args
    assert "OCR extraction failed (TesseractError)" in args[0]
    assert kwargs.get("ocr_language") == "fra"
