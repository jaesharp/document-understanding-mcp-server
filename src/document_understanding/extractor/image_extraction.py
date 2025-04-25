"""Functions related to extracting image information from PDFs."""

import fitz
import base64
import os
from typing import List, Optional, TYPE_CHECKING, Dict, Any

from ..exceptions import PDFExtractionError, PDFPasswordError

# Import stub types

# Use TYPE_CHECKING to avoid circular import
if TYPE_CHECKING:
    from .extractor import PDFExtractor  # Relative import for type hint


def _extract_images_impl(
    extractor: "PDFExtractor",  # Use type hint
    pdf_path: str,
    pages_str: Optional[str],
    include_data: bool = False,
    min_width: Optional[int] = None,
    min_height: Optional[int] = None,
    filter_bbox: Optional[List[float]] = None,  # [x0, y0, x1, y1]
    password: Optional[str] = None,  # Added password argument
    output_directory: Optional[str] = None,  # Directory to save extracted images
    save_without_returning_data: bool = False,  # Save images without returning data
) -> List[dict]:
    """
    Core implementation for extracting image information.
    Optionally saves images to files if output_directory is specified.
    """
    log = extractor.log  # Use extractor's logger
    log.debug(
        f"Entering _extract_images_impl for {pdf_path}, pages: {pages_str or 'all'}"
    )

    if not extractor.check_file_exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # Check if saving to files is enabled via feature flag
    save_images_enabled = (
        os.environ.get("ENABLE_SAVE_IMAGES_TO_FILES", "false").lower() == "true"
    )

    # Validate output_directory if specified
    if output_directory and not save_images_enabled:
        log.warning(
            "Saving images to files is disabled. Set ENABLE_SAVE_IMAGES_TO_FILES=true to enable."
        )
        output_directory = None  # Disable saving if feature flag is not set

    # Create output directory if specified and enabled
    if output_directory:
        # Validate the output directory path for security
        # Similar to how we handle allow-any-path
        allow_any_path = os.environ.get("ALLOW_ANY_PATH", "false").lower() == "true"

        if not allow_any_path:
            # Only allow paths within the configured safe directories
            safe_dirs = os.environ.get("SAFE_OUTPUT_DIRECTORIES", "").split(":")
            is_safe_path = False

            for safe_dir in safe_dirs:
                if safe_dir and os.path.commonpath(
                    [os.path.abspath(safe_dir), os.path.abspath(output_directory)]
                ) == os.path.abspath(safe_dir):
                    is_safe_path = True
                    break

            if not is_safe_path:
                log.warning(
                    f"Output directory {output_directory} is not within allowed safe directories. "
                    f"Set ALLOW_ANY_PATH=true to override or add to SAFE_OUTPUT_DIRECTORIES."
                )
                output_directory = None  # Disable saving if path is not safe

        if output_directory:
            try:
                os.makedirs(output_directory, exist_ok=True)
                log.info(f"Images will be saved to directory: {output_directory}")
            except Exception as dir_err:
                log.error(
                    f"Failed to create output directory: {output_directory}",
                    error=str(dir_err),
                )
                output_directory = None  # Disable saving if directory creation fails

    # Validate filter_bbox if provided
    filter_region_rect = None
    if filter_bbox:
        if len(filter_bbox) != 4:
            raise ValueError(
                "filter_bbox must be a list of 4 coordinates [x0, y0, x1, y1]."
            )
        if filter_bbox[0] >= filter_bbox[2] or filter_bbox[1] >= filter_bbox[3]:
            raise ValueError(
                "filter_bbox coordinates must be in the format [x0, y0, x1, y1] with x0 < x1 and y0 < y1."
            )
        filter_region_rect = fitz.Rect(filter_bbox)

    image_results = []
    doc = None  # Ensure doc is defined for finally block
    try:
        # Use the new helper method to open the document
        doc = extractor._open_pdf_document(pdf_path, password=password)

        total_pages = doc.page_count
        if total_pages == 0:
            log.info(f"PDF has 0 pages: {pdf_path}")
            return []

        # Parse pages *after* opening doc, but catch ValueError specifically
        try:
            selected_indices = extractor.parse_pages(pages_str, total_pages)
        except ValueError as page_parse_error:
            log.error(
                f"Invalid page specification for PDF '{pdf_path}'",
                error=str(page_parse_error),
            )
            # Wrap the ValueError in PDFExtractionError
            raise PDFExtractionError(
                f"Failed to process image extraction for PDF '{pdf_path}': {page_parse_error}"
            ) from page_parse_error

        if not selected_indices:
            log.warning("No valid pages selected for image extraction.")
            return []

        log.debug(f"Processing pages (0-based indices): {selected_indices}")

        for page_index in selected_indices:
            page_num_1_based = page_index + 1
            log.debug(f"Processing page {page_num_1_based}...")
            try:
                page = doc.load_page(page_index)
                # Get images from page
                img_list = page.get_images(full=True)
                if not img_list:
                    log.debug(f"No images found on page {page_num_1_based}")
                    continue
                log.debug(
                    f"Found {len(img_list)} raw image references on page {page_num_1_based}"
                )

                # Attempt to get bounding boxes first
                img_bboxes = None
                try:
                    # Get image rects
                    img_bboxes = page.get_image_rects(img_list, transform=False)
                    log.debug(
                        f"Successfully retrieved {len(img_bboxes)} bboxes for page {page_num_1_based}"
                    )
                except Exception as bbox_error:
                    log.warning(
                        "Failed to get bounding boxes for some images on page",
                        page_number=page_num_1_based,
                        pdf_path=pdf_path,
                        error=str(bbox_error),
                    )
                    # Proceed without bboxes if retrieval failed

                for i, img_info in enumerate(img_list):
                    # --- Filtering Logic Start ---
                    xref = img_info[0]
                    width = img_info[2]
                    height = img_info[3]
                    log.debug(
                        f"Processing image xref {xref} (w={width}, h={height}) on page {page_num_1_based}"
                    )

                    # 1. Filter by size
                    if min_width is not None and width < min_width:
                        log.debug(
                            "Image filtered out by min_width",
                            xref=xref,
                            width=width,
                            min_width=min_width,
                        )
                        continue
                    if min_height is not None and height < min_height:
                        log.debug(
                            "Image filtered out by min_height",
                            xref=xref,
                            height=height,
                            min_height=min_height,
                        )
                        continue

                    # 2. Get BBox for region filtering (if needed)
                    bbox_rect = None
                    if img_bboxes and i < len(img_bboxes):
                        bbox_candidate = img_bboxes[i]
                        if isinstance(bbox_candidate, fitz.Rect):
                            bbox_rect = bbox_candidate
                            log.debug(f"Found valid bbox for xref {xref}: {bbox_rect}")
                        else:
                            # Handle cases where an item in img_bboxes might not be a Rect
                            log.warning(
                                "Invalid bbox type encountered in list",
                                page_number=page_num_1_based,
                                xref=xref,
                                bbox_index=i,
                                bbox_type=type(bbox_candidate),
                            )
                            # Don't skip image, just proceed without bbox
                    else:
                        log.debug(f"No bbox found for image xref {xref} at index {i}")

                    # 3. Apply region filter (requires a valid bbox_rect)
                    if filter_region_rect is not None:
                        if bbox_rect is None:
                            log.debug(
                                "Image filtered out by region filter (missing bbox)",
                                xref=xref,
                            )
                            continue  # Cannot apply region filter without bbox
                        if not filter_region_rect.contains(bbox_rect):
                            log.debug(
                                "Image filtered out by region filter (not contained)",
                                xref=xref,
                                bbox=bbox_rect,
                                filter_region=filter_region_rect,
                            )
                            continue
                    # --- Filtering Logic End ---

                    log.debug(f"Image xref {xref} passed filters.")
                    # If image passes filters, proceed to build the result dict
                    img_desc = {
                        "page_number": page_num_1_based,
                        "xref": xref,
                        "width": width,
                        "height": height,
                    }
                    if bbox_rect:
                        img_desc["bbox"] = {
                            "x0": bbox_rect.x0,
                            "y0": bbox_rect.y0,
                            "x1": bbox_rect.x1,
                            "y1": bbox_rect.y1,
                        }
                    # else: bbox key is omitted if no valid bbox_rect

                    if include_data:
                        log.debug(f"Attempting to extract data for image xref {xref}")
                        try:
                            img_data = doc.extract_image(xref)
                            if img_data and img_data["image"]:
                                # Only include data in the response if save_without_returning_data is False
                                if not save_without_returning_data:
                                    img_desc["data"] = base64.b64encode(
                                        img_data["image"]
                                    ).decode("utf-8")
                                    img_desc["format"] = img_data["ext"]
                                    log.debug(
                                        f"Successfully extracted data for image xref {xref}, format: {img_data['ext']}"
                                    )
                                else:
                                    # Still set the format even if we're not returning the data
                                    img_desc["format"] = img_data["ext"]
                                    log.debug(
                                        f"Extracted data for image xref {xref} but not returning it in response, format: {img_data['ext']}"
                                    )

                                # Save image to file if output_directory is specified
                                if output_directory:
                                    try:
                                        # Generate a unique filename
                                        file_format = img_data["ext"]
                                        file_name = f"image_p{page_num_1_based}_x{xref}.{file_format}"
                                        file_path = os.path.join(
                                            output_directory, file_name
                                        )

                                        # Save the image to file
                                        with open(file_path, "wb") as f:
                                            f.write(img_data["image"])

                                        # Add file path to the result
                                        img_desc["file_path"] = file_path
                                        log.debug(f"Saved image to file: {file_path}")
                                    except Exception as save_err:
                                        log.warning(
                                            "Failed to save image to file",
                                            page_number=page_num_1_based,
                                            xref=xref,
                                            error=str(save_err),
                                        )
                            else:
                                log.warning(
                                    f"Extracted empty image data for xref {xref}",
                                    page_number=page_num_1_based,
                                )
                                img_desc["data"] = ""  # Indicate empty data explicitly
                                img_desc["format"] = (
                                    img_data.get("ext", "unknown")
                                    if img_data
                                    else "unknown"
                                )
                        except Exception as data_err:
                            log.warning(
                                "Failed to extract image data",
                                page_number=page_num_1_based,
                                xref=xref,
                                pdf_path=pdf_path,
                                error=str(data_err),
                            )
                            # Don't add data/format keys if extraction failed

                    image_results.append(img_desc)

            except Exception as page_error:
                log.warning(
                    f"Failed to process images for page index {page_index} ('{pdf_path}'): {page_error}",
                    exc_info=True,
                )
                # Don't add a partial page result, just log and continue
                continue

    except (PDFExtractionError, PDFPasswordError, ValueError) as e:
        # Re-raise specific known exceptions (including ValueError from parse_pages)
        raise e
    except Exception as e:
        log.error(f"Failed to process images for PDF '{pdf_path}': {e}", exc_info=True)
        # Wrap other exceptions
        raise PDFExtractionError(
            f"Failed to process images for PDF '{pdf_path}': {e}"
        ) from e
    finally:
        if doc:
            doc.close()
            log.debug(f"Closed PDF document: {pdf_path}")

    log.info(
        f"Successfully processed image extraction for '{pdf_path}'. Found {len(image_results)} filtered images."
    )
    return image_results
