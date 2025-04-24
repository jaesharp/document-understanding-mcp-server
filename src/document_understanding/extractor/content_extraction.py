# Module for content extraction logic

"""Functions related to extracting text content from PDF pages."""

import io
from typing import List, Optional, Dict, Any, TYPE_CHECKING, cast, Callable
from PIL import Image
from ..exceptions import PDFExtractionError
from src.document_understanding.exceptions import PDFPasswordError, OCRUnusableError

# Import stub types
from .fitz_stubs import PDFPage

if TYPE_CHECKING:
    from .extractor import PDFExtractor

# Type alias for OCR runner
OCRRunnerType = Callable[[Any, str], str]

# Constants for block structure
BBOX_INDICES = slice(0, 4)  # First 4 elements are bbox coordinates
TEXT_INDEX = 4  # 5th element is the text content

# Attempt to import TesseractError, handle if pytesseract not installed
try:
    from pytesseract import TesseractError as TesseractErrorType
except ImportError:

    class TesseractErrorType(Exception):  # type: ignore
        "Dummy exception if pytesseract is not installed."


# Type hints are imported from fitz_stubs.py

# Type hints are already imported above


def _perform_ocr(
    extractor_instance: "PDFExtractor",
    page: "PDFPage",
    ocr_language: Optional[str],
    page_num_log: int,
    context: str = "normal",
) -> str:
    """
    Helper function to perform OCR on a page and handle all related errors.

    Args:
        extractor_instance: The PDFExtractor instance
        page: The page to extract text from
        ocr_language: Language hint for OCR
        page_num_log: Page number for logging
        context: Context for logging (e.g., "forced", "fallback")

    Returns:
        Extracted text or error message
    """
    # Get logger and OCR runner
    logger = (
        extractor_instance.logger
        if hasattr(extractor_instance, "logger")
        else extractor_instance.log
    )
    _ocr_runner = extractor_instance._ocr_runner

    if _ocr_runner is None:
        return "[OCR runner is not available]"

    # Use specific log message formats based on context
    if context == "forced":
        logger.debug(
            f"Performing OCR on page {page_num_log} (forced)", page_number=page_num_log
        )
    else:
        logger.debug(
            f"Performing OCR fallback on page {page_num_log}", page_number=page_num_log
        )

    try:
        # Generate image from page
        pix = page.get_pixmap(dpi=300)
        img_bytes = pix.tobytes("png")
        if not img_bytes:
            # Match exact warning message format from tests
            if context == "forced":
                logger.warning(
                    "Pixmap generation resulted in empty bytes for OCR",
                    page_number=page_num_log,
                )
                return "[OCR failed: Pixmap empty]"
            else:
                logger.warning(
                    "Pixmap generation resulted in empty bytes for OCR fallback",
                    page_number=page_num_log,
                )
                return ""

        # Process image with OCR
        img = Image.open(io.BytesIO(img_bytes))
        ocr_text = _ocr_runner(img, ocr_language or "eng")

        # Log success with context-specific message
        if context == "forced":
            logger.debug(
                f"OCR successful for page {page_num_log}", page_number=page_num_log
            )
        else:
            logger.debug(
                f"OCR fallback successful for page {page_num_log}",
                page_number=page_num_log,
            )
        return cast(str, ocr_text.strip())

    except ImportError as e:
        # Match exact error message format from tests
        if context == "forced":
            logger.error(
                "OCR dependency missing during execution.",
                page_number=page_num_log,
                error=str(e),
            )
        else:
            logger.error(
                "OCR dependency missing during fallback execution.",
                page_number=page_num_log,
                error=str(e),
            )
        extractor_instance.ocr_enabled = False  # Disable OCR for future calls
        return f"[OCR failed: Dependency Error - {e}]"

    except TesseractErrorType as ts_error:
        # Match exact error message format from tests
        if context == "forced":
            logger.error(
                "OCR extraction failed (TesseractError)",
                page_number=page_num_log,
                error=str(ts_error),
                ocr_language=ocr_language,
            )
        else:
            logger.error(
                "OCR fallback failed (TesseractError)",
                page_number=page_num_log,
                error=str(ts_error),
                ocr_language=ocr_language,
            )
        return f"[OCR failed: {ts_error}]"

    except Exception as ocr_error:
        # Match exact error message format from tests
        if context == "forced":
            logger.error(
                "OCR extraction failed (generic error)",
                page_number=page_num_log,
                error=str(ocr_error),
                ocr_language=ocr_language,
                exc_info=True,
            )
        else:
            logger.error(
                "OCR fallback failed (generic error)",
                page_number=page_num_log,
                error=str(ocr_error),
                ocr_language=ocr_language,
                exc_info=True,
            )
        return f"[OCR failed: {ocr_error}]"


def _extract_page_text_impl(
    extractor_instance: "PDFExtractor",  # For logger and OCR runner access
    page: "PDFPage",
    ocr_language: Optional[str],
    force_ocr: bool = False,
) -> str:
    """
    Core implementation for extracting text from a single PDF page.

    Uses direct text extraction first, falls back to OCR if needed and enabled.
    Handles OCR forcing and error reporting.

    Args:
        extractor_instance: The PDFExtractor instance to use for extraction
        page: The PDF page to extract text from
        ocr_language: Language hint for OCR (if used)
        force_ocr: Whether to bypass direct extraction and use OCR

    Returns:
        Extracted text or error message
    """
    # Get logger from extractor instance
    logger = (
        extractor_instance.logger
        if hasattr(extractor_instance, "logger")
        else extractor_instance.log
    )

    ocr_enabled = extractor_instance.ocr_enabled
    _ocr_runner = extractor_instance._ocr_runner
    page_num_log = page.number  # For logging

    # Handle forced OCR if requested
    if force_ocr:
        # Check if OCR is available
        if not ocr_enabled:
            logger.warning(
                "OCR forced but unavailable (not enabled or configured).",
                page_number=page_num_log,
            )
            return "[OCR forced but unavailable]"

        if not _ocr_runner:
            logger.error(
                "OCR forced but runner is None (internal error).",
                page_number=page_num_log,
            )
            return "[OCR failed: Runner not available]"

        # Perform forced OCR
        return _perform_ocr(
            extractor_instance, page, ocr_language, page_num_log, context="forced"
        )

    # Try direct text extraction first (when not forcing OCR)
    try:
        text = page.get_text("text")
        logger.debug(
            f"Direct text extraction successful for page {page_num_log}",
            page_number=page_num_log,
        )
        return cast(str, text.strip())

    except Exception as text_error:
        # Direct extraction failed, try OCR fallback if enabled
        logger.warning(
            "Direct text extraction failed, attempting OCR fallback if enabled.",
            page_number=page_num_log,
            error=str(text_error),
        )

        # Check if OCR fallback is available
        if not ocr_enabled or not _ocr_runner:
            logger.debug(
                "OCR not enabled or runner missing, returning empty string after direct text failure.",
                page_number=page_num_log,
            )
            return ""

        # Perform OCR fallback
        return _perform_ocr(
            extractor_instance, page, ocr_language, page_num_log, context="fallback"
        )


def _extract_text_blocks(page, text: str, page_num: int, log) -> List[Any]:
    """
    Extract and format text blocks from a PDF page.

    Args:
        page: The PDF page
        text: The already extracted text (used as fallback)
        page_num: The 1-based page number (for logging)
        log: Logger instance

    Returns:
        List of text blocks
    """
    # Try to get blocks with blocks mode
    try:
        # Get text blocks
        text_blocks_result = page.get_text("blocks")
        # Ensure text_blocks is a list of the expected type
        if isinstance(text_blocks_result, list):
            return text_blocks_result
        else:
            # Handle unexpected return type
            log.warning(
                f"Unexpected text blocks format for page {page_num}",
                page_number=page_num,
            )
            return []
    except Exception as e:
        log.warning(
            f"Failed to get text blocks for page {page_num}, using simple text",
            error=str(e),
            page_number=page_num,
        )
        # Create a simple block with the text
        if text:
            # Convert to the expected format
            return [
                {
                    "bbox": [0, 0, 100, 100],
                    "text": text,
                    "type": 0,
                    "number": 0,
                }
            ]
        return []


def _format_blocks_for_response(text_blocks: List[Any]) -> List[Dict[str, Any]]:
    """
    Format text blocks into the response structure.

    Args:
        text_blocks: Raw text blocks from PyMuPDF

    Returns:
        Formatted blocks for API response
    """
    return [
        {
            "bbox": (block[BBOX_INDICES] if isinstance(block, tuple) else [0, 0, 0, 0]),
            "text": (
                block[TEXT_INDEX].strip()
                if isinstance(block, tuple) and len(block) > TEXT_INDEX
                else str(block).strip()
            ),
        }
        for block in text_blocks
    ]


def _process_single_page(
    extractor: "PDFExtractor",
    doc,
    page_index: int,
    force_ocr: bool,
    ocr_language: Optional[str],
) -> Dict[str, Any]:
    """
    Process a single PDF page to extract its text content.

    Args:
        extractor: The PDFExtractor instance
        doc: The PDF document
        page_index: 0-based index of the page to process
        force_ocr: Whether to force OCR for text extraction
        ocr_language: Language hint for OCR if used

    Returns:
        Dict containing page content information
    """
    log = extractor.log
    page_num = page_index + 1  # 1-based for logging/output

    try:
        log.debug(f"Processing page {page_num}")
        page = doc.load_page(page_index)

        text = ""  # Initialize text
        text_blocks: List[Any] = []  # Initialize blocks with proper type annotation

        # --- Check force_ocr flag --- #
        if force_ocr:
            log.debug(f"Force OCR requested for page {page_num}")
            # Use the internal helper that handles OCR logic
            # Ensure ocr_language is not None
            final_ocr_language = ocr_language or "eng"  # Default to English if None
            text = _extract_page_text_impl(
                extractor, page, final_ocr_language, force_ocr=True
            )
            # When forcing OCR, we don't get detailed blocks from this helper
            text_blocks = []
            # Log if OCR might have failed (helper returns specific strings)
            if text.startswith("[OCR failed") or text.startswith(
                "[OCR forced but unavailable]"
            ):
                log.warning(
                    f"Forced OCR for page {page_num} resulted in status: {text}"
                )
            elif not text:
                log.warning(f"Forced OCR for page {page_num} returned empty text.")
        else:
            # --- Default: Direct Text Extraction --- #
            log.debug(f"Attempting direct text extraction for page {page_num}")
            text = page.get_text("text")  # Basic text extraction

            # Extract text blocks
            text_blocks = _extract_text_blocks(page, text, page_num, log)

            # Simple check if text seems empty or just whitespace
            if not text or text.isspace():
                log.warning(
                    f"Page {page_num}: No significant text found via direct extraction."
                )
                text = ""  # Ensure text is empty string if no content
                text_blocks = []  # Ensure blocks are empty too

        # Format the result
        return {
            "page": page_num,
            "content": text.strip() if text else "",
            "blocks": _format_blocks_for_response(text_blocks),
        }

    except Exception as page_error:
        log.warning(
            f"Failed to extract text for page {page_num}",
            pdf_path=doc.name,
            page_index=page_index,
            error=str(page_error),
            exc_info=True,  # Include traceback in log
        )
        # Return error information
        return {"page": page_num, "error": f"Failed to process page: {page_error}"}


def _extract_content_impl(
    extractor: "PDFExtractor",  # Use type hint
    pdf_path: str,
    pages_str: Optional[str],
    ocr_language: Optional[str],
    force_ocr: bool,
    password: Optional[str] = None,  # Added password argument
) -> List[Dict[str, Any]]:
    """
    Implementation logic for extracting text content from specified PDF pages.
    Handles page selection, OCR fallback (though currently disabled).

    Args:
        extractor: The PDFExtractor instance
        pdf_path: Path to the PDF file
        pages_str: String specifying which pages to process (e.g., "1-3,5,7-9")
        ocr_language: Language hint for OCR if used
        force_ocr: Whether to force OCR for text extraction
        password: Optional password for encrypted PDFs

    Returns:
        List of dictionaries containing page content information
    """
    log = extractor.log  # Get logger from extractor instance
    log.debug(f"Entering _extract_content_impl for {pdf_path}, pages: {pages_str}")

    # --- OCR Capability Check ---
    ocr_available = extractor.is_ocr_available()
    if force_ocr and not ocr_available:
        log.error("OCR force requested, but OCR is disabled or unusable.")
        raise OCRUnusableError("OCR force requested, but OCR is disabled or unusable.")

    # Check if file exists
    if not extractor.check_file_exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    results = []
    processed_pages = set()
    doc = None

    try:
        # Open the document
        doc = extractor._open_pdf_document(pdf_path, password=password)

        # Determine pages to process
        page_indices = extractor.parse_pages(pages_str, doc.page_count)
        if not page_indices:
            log.warning("No valid pages specified or PDF is empty.")
            return []

        log.info(f"Processing {len(page_indices)} pages: {[p+1 for p in page_indices]}")

        # Process each page
        for page_index in page_indices:
            if page_index in processed_pages:
                continue

            result = _process_single_page(
                extractor, doc, page_index, force_ocr, ocr_language
            )
            results.append(result)
            processed_pages.add(page_index)

    except (PDFExtractionError, PDFPasswordError) as e:
        # Re-raise specific exceptions
        raise e
    except Exception as e:
        log.error(f"Error processing PDF '{pdf_path}': {e}", exc_info=True)
        raise PDFExtractionError(
            f"Failed to extract content from '{pdf_path}': {e}"
        ) from e
    finally:
        if doc:
            doc.close()
            log.debug(f"Closed PDF document: {pdf_path}")

    log.info(
        f"Successfully extracted content from {len(results)} pages of '{pdf_path}'."
    )
    return results
