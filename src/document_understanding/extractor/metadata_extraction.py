# Module for metadata extraction logic

"""Functions related to extracting metadata from PDF files"""

from typing import Dict, Any, Optional, TYPE_CHECKING

from ..exceptions import PDFExtractionError, PDFPasswordError

# Import stub types

# Use TYPE_CHECKING to avoid circular import
if TYPE_CHECKING:
    from .extractor import PDFExtractor  # Relative import for type hint


def _extract_metadata_impl(
    extractor: "PDFExtractor",  # Use type hint
    pdf_path: str,
    password: Optional[str] = None,  # Added password argument
    max_pages_for_metadata_scan: int = 100,  # Added max_pages_for_metadata_scan argument
) -> Dict[str, Any]:
    """
    Implementation logic for extracting metadata and checking for images/drawings.
    """
    log = extractor.log
    log.debug(f"Entering _extract_metadata_impl for {pdf_path}")

    if not extractor.check_file_exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    metadata = {}
    has_embedded_images = False
    has_drawings = False
    doc = None
    page_count = 0  # Initialise page_count

    try:
        # Use the new helper method to open the document
        doc = extractor._open_pdf_document(pdf_path, password=password)
        page_count = doc.page_count  # Get page_count here

        metadata = doc.metadata
        log.debug(f"Raw metadata extracted: {metadata}")

        # Scan pages for images/drawings (up to a limit)
        scan_limit = min(doc.page_count, max_pages_for_metadata_scan)
        for i in range(scan_limit):
            try:
                page = doc.load_page(i)
                if page.get_images(full=False):  # Check if list is non-empty
                    has_embedded_images = True
                if page.get_drawings():  # Check if list is non-empty
                    has_drawings = True
                # Early exit if both found
                if has_embedded_images and has_drawings:
                    break
            except Exception as page_error:
                log.warning(
                    f"Error scanning page {i+1} for metadata elements: {page_error}",
                    exc_info=True,
                )
                # Continue scanning other pages if possible

    except (PDFExtractionError, PDFPasswordError) as e:
        # Re-raise specific exceptions
        raise e
    except Exception as e:
        log.error(f"Error extracting metadata from '{pdf_path}': {e}", exc_info=True)
        # It might be okay to return partial metadata if the doc opened but failed later
        # However, for consistency, we raise an error if anything goes wrong.
        raise PDFExtractionError(
            f"Failed to extract metadata from '{pdf_path}': {e}"
        ) from e
    finally:
        if doc:
            doc.close()
            log.debug(f"Closed PDF document: {pdf_path}")

    # page_count is now correctly set from within the try block or defaults to 0

    result = {
        "page_count": page_count,
        "metadata": metadata,
        "has_embedded_images": has_embedded_images,
        "has_drawings": has_drawings,
    }
    log.info(
        f"Successfully extracted metadata from '{pdf_path}'."
        f" Pages: {page_count}, Images: {has_embedded_images}, Drawings: {has_drawings}"
    )
    return result
