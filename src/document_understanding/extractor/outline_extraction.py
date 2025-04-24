# Module for outline (TOC/Bookmark) extraction logic
from typing import List, Optional, TYPE_CHECKING  # Added Optional, TYPE_CHECKING

from ..models import OutlineItem  # Assuming OutlineItem is in models
from ..exceptions import PDFExtractionError, PDFPasswordError  # Added exceptions

# Import stub types

# Use TYPE_CHECKING to avoid circular import
if TYPE_CHECKING:
    from .extractor import PDFExtractor  # Relative import for type hint


# --- Helper Function moved from PDFExtractor --- #
def _parse_toc_recursive_impl(
    toc_list: list, current_level: int = 1
) -> List[OutlineItem]:
    """Helper to recursively parse fitz.get_toc() into nested OutlineItem structure."""
    result = []
    i = 0
    while i < len(toc_list):
        level, title, page = toc_list[i][:3]  # Ignore destination details for now
        page_1based = page + 1  # fitz uses 0-based, we want 1-based

        if level == current_level:
            item = OutlineItem(title=title, level=level, page_number=page_1based)
            # Look ahead for children
            children_toc = []
            j = i + 1
            while j < len(toc_list) and toc_list[j][0] > current_level:
                children_toc.append(toc_list[j])
                j += 1

            if children_toc:
                # Use self._parse_toc_recursive for the recursive call
                item.children = _parse_toc_recursive_impl(
                    children_toc, current_level + 1
                )

            result.append(item)
            i = j  # Move main index past the children we just processed
        elif level < current_level:
            # This level is handled by the parent call, stop processing here
            break
        else:  # level > current_level
            # Skip levels deeper than expected (should be handled by child recursion)
            i += 1

    return result


def _extract_outline_impl(
    extractor: "PDFExtractor",  # Updated type hint
    pdf_path: str,
    password: Optional[str] = None,  # Added password argument
) -> List[OutlineItem]:
    """
    Core implementation for extracting the document outline (TOC/Bookmarks).
    """
    log = extractor.log  # Use extractor's logger
    log.debug(f"Entering _extract_outline_impl for {pdf_path}")

    if not extractor.check_file_exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    doc = None  # Ensure doc is defined outside try for potential error logging
    try:
        # Use the new helper method to open the document with password
        doc = extractor._open_pdf_document(pdf_path, password=password)

        toc = doc.get_toc()
        if not toc:
            log.info(f"No outline (TOC) found in {pdf_path}")
            return []  # Return empty list if no TOC

        # Parse the flat list into nested structure using the moved helper
        parsed_outline = _parse_toc_recursive_impl(toc)
        log.info(f"Successfully extracted outline from {pdf_path}")
        return parsed_outline

    except (PDFExtractionError, PDFPasswordError) as e:
        # Re-raise specific exceptions
        raise e
    except Exception as e:
        log.error(f"Error extracting outline from '{pdf_path}': {e}", exc_info=True)
        # Re-raise a more specific error for the server handler
        raise PDFExtractionError(
            f"Failed to extract outline from '{pdf_path}': {e}"
        ) from e
    finally:
        if doc:
            doc.close()
            log.debug(f"Closed PDF document: {pdf_path}")
