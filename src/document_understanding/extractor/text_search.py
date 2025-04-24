# Module for text search logic

"""Functions for searching text within PDF documents."""

from typing import List, Optional, TYPE_CHECKING

from ..exceptions import PDFExtractionError, PDFPasswordError

# Import stub types

# Use TYPE_CHECKING to avoid circular import
if TYPE_CHECKING:
    from .extractor import PDFExtractor  # Relative import for type hint


def _search_text_impl(
    extractor: "PDFExtractor",  # Updated type hint
    pdf_path: str,
    query: str,
    pages_str: Optional[str],
    password: Optional[str] = None,  # Added password argument
) -> List[dict]:
    """
    Core implementation for searching text within specified pages.
    (Moved from PDFExtractor.search_text)
    """
    log = extractor.log  # Use extractor's logger
    log.debug(
        f"Entering _search_text_impl for {pdf_path}, query: '{query}', pages: {pages_str or 'all'}"
    )

    # Use extractor's helpers
    _file_exists = extractor.check_file_exists
    _open_pdf = extractor._open_pdf_document
    parse_pages = extractor.parse_pages

    if not pdf_path or not _file_exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found at: {pdf_path}")
    if not query:
        raise ValueError("Search query cannot be empty.")

    search_results = []
    try:
        with _open_pdf(pdf_path, password=password) as doc:
            total_pages = doc.page_count
            if total_pages == 0:
                return []

            selected_indices = parse_pages(pages_str, total_pages)

            for page_index in selected_indices:
                try:
                    page = doc.load_page(page_index)
                    # search_for returns a list of Rect objects
                    found_rects = page.search_for(query, quads=False)  # Get rectangles
                    for rect in found_rects:
                        search_results.append(
                            {
                                "page": page_index + 1,  # 1-based for output
                                "rect": [rect.x0, rect.y0, rect.x1, rect.y1],
                            }
                        )
                except Exception as page_error:
                    log.warning(
                        f"Failed to search page index {page_index} in '{pdf_path}': {page_error}",
                        exc_info=True,
                    )
                    # Optionally add an error marker? For now, just skip failed pages in search.

    except (PDFExtractionError, PDFPasswordError) as e:
        # Re-raise specific known exceptions
        raise e
    except Exception as e:
        log.error(f"Failed to search PDF '{pdf_path}': {e}", exc_info=True)
        # Wrap other exceptions
        raise PDFExtractionError(f"Failed to search PDF '{pdf_path}': {e}") from e

    return search_results
