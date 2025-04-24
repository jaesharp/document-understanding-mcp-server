"""Functions related to extracting page layout information from PDFs."""

import fitz
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from ..models import (
    Rect as RectModel,  # noqa: F401 - Used for type annotations
    SimpleImageInfo,  # noqa: F401 - Used for type annotations
    Rect,  # noqa: F401 - Used for type annotations
)  # Type annotations used throughout this module
from ..exceptions import PDFExtractionError, PDFPasswordError

# Import stub types

# Use TYPE_CHECKING to avoid circular import
if TYPE_CHECKING:
    from .extractor import PDFExtractor  # Relative import for type hint


# Define the implementation function
def _extract_layout_impl(
    extractor: "PDFExtractor",  # Updated type hint
    pdf_path: str,
    pages_str: Optional[str],
    include_images: bool = False,
    include_drawings: bool = False,
    detail_level: Optional[str] = None,
    password: Optional[str] = None,  # Added password argument
) -> List[dict]:
    """
    Core implementation for extracting layout information from specified pages.
    """
    log = extractor.log  # Use extractor's logger
    log.debug(
        f"Entering _extract_layout_impl for {pdf_path}, pages: {pages_str or 'all'}"
    )

    if not extractor.check_file_exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    layout_results = []
    doc = None  # Ensure doc is defined for finally block
    try:
        # Use the new helper method to open the document
        doc = extractor._open_pdf_document(pdf_path, password=password)

        total_pages = doc.page_count
        if total_pages == 0:
            log.info(f"PDF has 0 pages: {pdf_path}")
            return []

        selected_indices = extractor.parse_pages(pages_str, total_pages)
        log.debug(f"Processing pages (0-based indices): {selected_indices}")

        for page_index in selected_indices:
            page_num_1_based = page_index + 1
            log.debug(f"Processing page {page_num_1_based}...")
            # Initialize page layout dict
            page_layout = {
                "page_number": page_num_1_based,
                "text_blocks": [],
            }
            if include_drawings:
                page_layout["drawings"] = []
            if include_images:
                page_layout["images"] = []

            try:
                page = doc.load_page(page_index)
                # Extract text blocks
                # Get text as a dict with text flags
                raw_dict_text = page.get_text("dict", flags=fitz.TEXTFLAGS_TEXT)
                # Ensure raw_dict is a dict for type checking
                raw_dict: Dict[str, Any] = {}
                if isinstance(raw_dict_text, dict):
                    raw_dict = raw_dict_text
                else:
                    # For type checking, create a dummy dict
                    raw_dict = {"blocks": []}
                processed_blocks = []
                # Get blocks from raw_dict
                blocks = raw_dict.get("blocks", [])
                if not isinstance(blocks, list):
                    blocks = []

                for block in blocks:
                    try:
                        # Basic validation/processing for now
                        # Enhance this later based on required detail level
                        block_num = block.get("number")
                        block_type = block.get("type")  # 0 for text, 1 for image
                        bbox = block.get("bbox")

                        if block_type == 0:  # Process text block
                            processed_lines = []
                            # Get lines from block or use empty list
                            lines = block.get("lines", [])
                            # Make sure lines is iterable
                            if not isinstance(lines, list):
                                lines = []
                                log.warning(
                                    f"Block {block.get('number', '?')} has invalid lines format",
                                    block_number=block.get("number", "?"),
                                    error="Bad Line Iter",
                                )
                            for line in lines:
                                processed_spans = []
                                if "spans" in line:
                                    for span in line["spans"]:
                                        # Basic span info - enhance later if needed
                                        processed_spans.append(
                                            {
                                                "text": span.get("text", ""),
                                                "font": span.get("font", ""),
                                                "size": span.get("size", 0.0),
                                                "flags": span.get("flags", 0),
                                                "color": span.get("color", 0),
                                                "bbox": span.get("bbox"),
                                            }
                                        )
                                processed_lines.append(
                                    {"bbox": line.get("bbox"), "spans": processed_spans}
                                )
                            processed_blocks.append(
                                {
                                    "number": block_num,
                                    "type": block_type,
                                    "bbox": bbox,
                                    "lines": processed_lines,
                                }
                            )
                        # Note: Image blocks (type 1) are typically handled by get_images
                        # We might skip them here unless specific image block info is needed

                    except Exception as block_err:
                        log.warning(
                            "Skipping invalid block due to processing error",
                            page_number=page_num_1_based,
                            block_number=block.get("number", "N/A"),
                            pdf_path=pdf_path,
                            error=str(block_err),
                            # Removed exc_info for brevity, add back if needed for debug
                        )
                page_layout["text_blocks"] = processed_blocks

                # Extract drawings only if requested
                if include_drawings:
                    try:
                        drawings = page.get_drawings()
                        # TODO: Potentially simplify/model the drawing data
                        page_layout["drawings"] = drawings
                        log.debug(
                            f"Extracted {len(drawings)} drawing paths from page {page_num_1_based}"
                        )
                    except Exception as draw_err:
                        log.warning(
                            "Error extracting drawings",
                            page_number=page_num_1_based,
                            pdf_path=pdf_path,
                            error=str(draw_err),
                        )
                        # page_layout["drawings"] already initialized

                # Extract image info only if requested
                if include_images:
                    try:
                        # Get images from page
                        img_list = page.get_images(full=True)
                        if img_list:
                            img_bboxes = None
                            try:
                                # Get image rects
                                img_bboxes = page.get_image_rects(
                                    img_list, transform=False
                                )
                            except Exception as bbox_error:
                                log.warning(
                                    "Failed to get bounding boxes for some images on page",
                                    page_number=page_num_1_based,
                                    pdf_path=pdf_path,
                                    error=str(bbox_error),
                                )

                            page_images = []
                            for i, img_info in enumerate(img_list):
                                try:  # Wrap processing for EACH image
                                    xref = img_info[0]
                                    width = img_info[2]
                                    height = img_info[3]
                                    bbox_rect = None

                                    if (
                                        img_bboxes
                                        and i < len(img_bboxes)
                                        and isinstance(img_bboxes[i], fitz.Rect)
                                    ):
                                        bbox_rect = img_bboxes[i]
                                    elif (
                                        img_bboxes
                                        and i < len(img_bboxes)
                                        and img_bboxes[i] is not None
                                    ):
                                        log.warning(
                                            "Invalid bbox type encountered in list",
                                            page_number=page_num_1_based,
                                            xref=xref,
                                            bbox_index=i,
                                            bbox_type=type(img_bboxes[i]),
                                        )
                                        # Skip image if bbox invalid?
                                        # continue # Let's not skip, just omit bbox

                                    img_desc_dict = {
                                        "xref": xref,
                                        "width": width,
                                        "height": height,
                                    }
                                    if bbox_rect:
                                        img_desc_dict["bbox"] = {
                                            "x0": bbox_rect.x0,
                                            "y0": bbox_rect.y0,
                                            "x1": bbox_rect.x1,
                                            "y1": bbox_rect.y1,
                                        }

                                    page_images.append(img_desc_dict)

                                except Exception as img_err:
                                    current_xref = (
                                        img_info[0]
                                        if isinstance(img_info, (list, tuple))
                                        and len(img_info) > 0
                                        else "N/A"
                                    )
                                    log.warning(
                                        "Skipping image in layout due to processing error",
                                        page_number=page_num_1_based,
                                        img_index=i,
                                        xref=current_xref,
                                        error=str(img_err),
                                    )
                                    continue
                            page_layout["images"] = page_images
                            log.debug(
                                f"Extracted info for {len(page_images)} images from page {page_num_1_based}"
                            )
                    except Exception as img_proc_err:
                        log.warning(
                            "Error processing images for page layout",
                            page_number=page_num_1_based,
                            pdf_path=pdf_path,
                            error=str(img_proc_err),
                        )
                        # page_layout["images"] already initialized

                layout_results.append(page_layout)

            except Exception as page_error:
                log.warning(
                    f"Failed to extract layout for page index {page_index} ('{pdf_path}')",
                    error=str(page_error),
                    exc_info=True,
                )
                # Add page with error indicator
                page_layout["error"] = f"{type(page_error).__name__}: {page_error}"
                layout_results.append(page_layout)  # Append even if page failed

    except (PDFExtractionError, PDFPasswordError) as e:
        # Re-raise specific known exceptions
        raise e
    except Exception as e:
        log.error(
            f"Failed to process layout for PDF '{pdf_path}'",
            error=str(e),
            exc_info=True,
        )
        # Wrap other exceptions
        raise PDFExtractionError(
            f"Failed to process layout for PDF '{pdf_path}': {e}"
        ) from e
    finally:
        if doc:
            doc.close()
            log.debug(f"Closed PDF document: {pdf_path}")

    log.info(
        f"Successfully processed layout extraction for '{pdf_path}'. Pages processed: {len(layout_results)}"
    )
    return layout_results


# Placeholder for potential future layout-specific helper functions
