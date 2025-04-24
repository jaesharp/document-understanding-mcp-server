# Module for language detection logic
from langdetect import detect_langs, LangDetectException, DetectorFactory
from typing import Optional, TYPE_CHECKING
from ..logging_config import get_logger

# Use TYPE_CHECKING to avoid circular import
if TYPE_CHECKING:
    from .extractor import PDFExtractor  # Relative import for type hint

logger = get_logger(__name__)

# Ensure consistent language detection results for short/ambiguous text
# (This might be better placed globally if DetectorFactory is used elsewhere)
DetectorFactory.seed = 0


def _detect_language_impl(
    extractor_instance: "PDFExtractor",  # Added type hint
    pdf_path: str,
    pages_str: Optional[str] = "1",
    sample_size: Optional[int] = 2000,
    password: Optional[str] = None,  # Added password argument
) -> dict:
    """
    Core implementation for detecting language from text samples.
    Now accepts a password argument.
    """
    log = extractor_instance.log  # Use instance's logger
    _file_exists = extractor_instance.check_file_exists
    extract_content_func = extractor_instance.extract_content

    log.info("Attempting language detection (impl)", pdf_path=pdf_path, pages=pages_str)
    if not pdf_path or not _file_exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

    # Ensure we have a valid sample size
    if sample_size is None or sample_size <= 0:
        sample_size = 2000  # Default to 2000 characters if invalid or None

    # 1. Extract a text sample using the existing content extraction
    try:
        sample_pages = pages_str if pages_str and pages_str.strip() else "1"
        # Call the extract_content method on the passed instance, INCLUDING password
        content_list = extract_content_func(pdf_path, sample_pages, password=password)
        if not content_list:
            raise ValueError(
                "No text content found on specified sample pages to detect language."
            )
        # Extract only the text part from the dictionary results
        full_sample = "\n".join(item.get("text", "") for item in content_list)
        text_sample = full_sample[:sample_size].strip()
        if not text_sample:
            raise ValueError("Extracted text sample is empty, cannot detect language.")
    except ValueError as ve:
        log.error(
            "Failed to get text sample for language detection",
            pdf_path=pdf_path,
            pages=pages_str,
            error=str(ve),
        )
        raise ValueError(
            f"Could not extract text sample for language detection: {ve}"
        ) from ve
    except Exception as e:
        # Handle password errors specifically if they bubble up from extract_content
        from ..exceptions import PDFPasswordError  # Local import ok here

        if isinstance(e, PDFPasswordError):
            log.warning(
                "Password error while extracting text sample for language detection",
                pdf_path=pdf_path,
            )
            raise e  # Re-raise the password error
        log.error(
            "Unexpected error getting text sample",
            pdf_path=pdf_path,
            pages=pages_str,
            error=str(e),
            exc_info=True,
        )
        raise ValueError(
            f"Could not extract text sample for language detection: {e}"
        ) from e

    # 2. Perform language detection on the sample
    try:
        detected_langs = detect_langs(text_sample)
        detections = [
            {"language_code": lang.lang, "confidence": lang.prob}
            for lang in detected_langs
        ]
        return {"detections": detections, "text_sample_used": text_sample}
    except LangDetectException as lde:
        log.warning("Language detection failed", pdf_path=pdf_path, error=str(lde))
        # Re-raise as ValueError for the server
        raise ValueError(f"Could not reliably detect language: {lde}") from lde
