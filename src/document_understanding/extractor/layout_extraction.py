"""Functions related to extracting page layout information from PDFs."""

import fitz
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from ..models import (  # noqa: F401 - Used for type annotations
    Rect as RectModel,  # noqa: F401 - Used for type annotations
    SimpleImageInfo,  # noqa: F401 - Used for type annotations
    Rect,  # noqa: F401 - Used for type annotations
    Point,  # noqa: F401 - Used for type annotations
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
                                        # Convert bbox to dictionary format
                                        span_bbox = _convert_bbox_to_dict(
                                            span.get("bbox")
                                        )

                                        # Get required fields for TextSpan
                                        # Convert origin to dictionary format
                                        origin_point = _convert_point_to_dict(
                                            span.get("origin")
                                        )

                                        span_dict = {
                                            "text": span.get("text", ""),
                                            "font": span.get("font", ""),
                                            "size": span.get("size", 0.0),
                                            "flags": span.get("flags", 0),
                                            "color": span.get("color", 0),
                                            "ascender": span.get(
                                                "ascender", 0.8
                                            ),  # Default values for required fields
                                            "descender": span.get("descender", -0.2),
                                            "origin": (
                                                origin_point
                                                if origin_point
                                                else {"x": 0, "y": 0}
                                            ),
                                            "bbox": (
                                                span_bbox
                                                if span_bbox
                                                else {
                                                    "x0": 0,
                                                    "y0": 0,
                                                    "x1": 0,
                                                    "y1": 0,
                                                }
                                            ),
                                        }
                                        processed_spans.append(span_dict)
                                # Convert line bbox to dictionary format
                                line_bbox = _convert_bbox_to_dict(line.get("bbox"))

                                # Get required fields for TextLine
                                # Convert dir to dictionary format
                                dir_point = _convert_point_to_dict(line.get("dir"))

                                line_dict = {
                                    "bbox": (
                                        line_bbox
                                        if line_bbox
                                        else {"x0": 0, "y0": 0, "x1": 0, "y1": 0}
                                    ),
                                    "spans": processed_spans,
                                    "wmode": line.get(
                                        "wmode", 0
                                    ),  # Default values for required fields
                                    "dir": dir_point if dir_point else {"x": 1, "y": 0},
                                }
                                processed_lines.append(line_dict)
                            # Convert block bbox to dictionary format
                            block_bbox = _convert_bbox_to_dict(bbox)

                            processed_blocks.append(
                                {
                                    "number": block_num,
                                    "type": block_type,
                                    "bbox": (
                                        block_bbox
                                        if block_bbox
                                        else {"x0": 0, "y0": 0, "x1": 0, "y1": 0}
                                    ),
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
                        # Process drawings to ensure they are serializable
                        processed_drawings = _process_drawings_for_serialization(
                            drawings
                        )
                        page_layout["drawings"] = processed_drawings
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
                                # First try with transform=False (preserves original coordinates)
                                # Check if we have a valid image list
                                if not img_list or not all(
                                    isinstance(img, tuple) for img in img_list
                                ):
                                    log.warning(
                                        "Invalid image list format",
                                        page_number=page_num_1_based,
                                    )
                                    img_bboxes = (
                                        [None] * len(img_list) if img_list else []
                                    )
                                else:
                                    try:
                                        # First try with transform=False (preserves original coordinates)
                                        img_bboxes = page.get_image_rects(
                                            img_list, transform=False
                                        )
                                    except Exception:
                                        # If that fails, try with transform=True (applies page transformation)
                                        try:
                                            log.debug(
                                                "Retrying get_image_rects with transform=True",
                                                page_number=page_num_1_based,
                                            )
                                            img_bboxes = page.get_image_rects(
                                                img_list, transform=True
                                            )
                                        except Exception as e2:
                                            # If both methods fail, create empty bounding boxes
                                            log.debug(
                                                "Creating default bounding boxes for images",
                                                page_number=page_num_1_based,
                                            )
                                            # Create a list of None values with the same length as img_list
                                            img_bboxes = [None] * len(img_list)
                                            # Don't re-raise the exception, just log it
                                            log.warning(
                                                "Failed to get image bounding boxes, using None values",
                                                page_number=page_num_1_based,
                                                error=str(e2),
                                                image_count=len(img_list),
                                                note="Images without bounding boxes will be included in the output, but their positions will be unknown. This may affect layout analysis and visual representation.",
                                            )
                            except Exception as bbox_error:
                                log.warning(
                                    "Failed to get bounding boxes for some images on page",
                                    page_number=page_num_1_based,
                                    pdf_path=pdf_path,
                                    error=str(bbox_error),
                                    image_count=len(img_list) if img_list else 0,
                                    note="Images without bounding boxes will be included in the output, but their positions will be unknown. This may affect layout analysis and visual representation.",
                                )
                                # Ensure img_bboxes is initialized even if an exception occurs
                                if img_bboxes is None:
                                    img_bboxes = (
                                        [None] * len(img_list) if img_list else []
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
                                        # Always include bbox field, even if None, to satisfy the model
                                        "bbox": (
                                            _convert_bbox_to_dict(bbox_rect)
                                            if bbox_rect
                                            else None
                                        ),
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


def _convert_bbox_to_dict(bbox) -> Optional[Dict[str, float]]:
    """
    Convert a bbox from various formats to a dictionary format suitable for Pydantic models.

    This function is critical for handling bounding boxes in the layout extraction process.
    PyMuPDF returns bounding boxes in various formats (tuples, fitz.Rect objects), but the
    Pydantic models expect dictionaries with specific keys. This function handles the conversion
    and provides robust error handling.

    When a bounding box cannot be converted (e.g., it's None or in an unsupported format),
    the function returns None. The calling code should handle this case appropriately,
    typically by providing a default bounding box or skipping the element.

    Args:
        bbox: A bounding box in tuple format (x0, y0, x1, y1), list format [x0, y0, x1, y1],
              fitz.Rect object, or dictionary with x0, y0, x1, y1 keys

    Returns:
        A dictionary with x0, y0, x1, y1 keys, or None if the input is invalid
    """
    if bbox is None:
        return None

    # Handle fitz.Rect objects
    if isinstance(bbox, fitz.Rect):
        return {"x0": bbox.x0, "y0": bbox.y0, "x1": bbox.x1, "y1": bbox.y1}

    # Handle tuples and lists
    if isinstance(bbox, (tuple, list)) and len(bbox) >= 4:
        return {
            "x0": float(bbox[0]),
            "y0": float(bbox[1]),
            "x1": float(bbox[2]),
            "y1": float(bbox[3]),
        }

    # Handle dictionaries
    if isinstance(bbox, dict) and all(k in bbox for k in ["x0", "y0", "x1", "y1"]):
        return {
            "x0": float(bbox["x0"]),
            "y0": float(bbox["y0"]),
            "x1": float(bbox["x1"]),
            "y1": float(bbox["y1"]),
        }

    # If we get here, the bbox is in an unsupported format
    return None


# Other layout-specific helper functions


def _convert_point_to_dict(point) -> Optional[Dict[str, float]]:
    """
    Convert a point from various formats to a dictionary format suitable for Pydantic models.

    This function handles PyMuPDF Point objects, tuples, lists, and dictionaries.

    Args:
        point: A point in PyMuPDF Point format, tuple format (x, y), list format [x, y],
              or dictionary with x, y keys

    Returns:
        A dictionary with x, y keys, or None if the input is invalid
    """
    if point is None:
        return None

    # Handle PyMuPDF Point objects
    if hasattr(point, "x") and hasattr(point, "y"):
        return {"x": float(point.x), "y": float(point.y)}

    # Handle tuples and lists
    if isinstance(point, (tuple, list)) and len(point) >= 2:
        return {"x": float(point[0]), "y": float(point[1])}

    # Handle dictionaries
    if isinstance(point, dict) and all(k in point for k in ["x", "y"]):
        return {"x": float(point["x"]), "y": float(point["y"])}

    # If we get here, the point is in an unsupported format
    return None


def _process_drawings_for_serialization(drawings: List[Dict]) -> List[Dict]:
    """
    Process drawings to ensure they are serializable.

    This function converts any PyMuPDF-specific objects (like Point) to dictionaries.

    Args:
        drawings: List of drawing dictionaries from PyMuPDF

    Returns:
        List of serializable drawing dictionaries
    """
    from typing import Any, Dict

    processed_drawings = []

    for drawing in drawings:
        # Create a new dict to avoid modifying the original
        processed_drawing: Dict[str, Any] = {}

        # Process each key in the drawing dict
        for key, value in drawing.items():
            # Handle items that might be PyMuPDF Rect objects
            if key == "rect" and hasattr(value, "x0"):
                processed_drawing[key] = _convert_bbox_to_dict(value)
            # Handle items that might be PyMuPDF Point objects
            elif (
                key in ["start", "end", "point"]
                and hasattr(value, "x")
                and hasattr(value, "y")
            ):
                processed_drawing[key] = _convert_point_to_dict(value)
            # Handle lists that might contain Point objects
            elif key == "points" and isinstance(value, list):
                # Create a list of processed points
                processed_points = [
                    (
                        _convert_point_to_dict(p)
                        if hasattr(p, "x") and hasattr(p, "y")
                        else p
                    )
                    for p in value
                ]
                processed_drawing[key] = processed_points
            # Handle 'items' list which might contain tuples with Rect objects
            elif key == "items" and isinstance(value, list):
                processed_items = []
                for item in value:
                    if isinstance(item, tuple):
                        # Process tuple items
                        processed_tuple = list(item)  # Convert to list for modification
                        # Check if any element is a Rect
                        for i, elem in enumerate(processed_tuple):
                            if (
                                hasattr(elem, "x0")
                                and hasattr(elem, "y0")
                                and hasattr(elem, "x1")
                                and hasattr(elem, "y1")
                            ):
                                processed_tuple[i] = _convert_bbox_to_dict(elem)
                        processed_items.append(
                            tuple(processed_tuple)
                        )  # Convert back to tuple
                    else:
                        processed_items.append(item)
                # Assign the processed items to the key
                processed_drawing[key] = processed_items
            # Handle other values
            else:
                processed_drawing[key] = value

        processed_drawings.append(processed_drawing)

    return processed_drawings
