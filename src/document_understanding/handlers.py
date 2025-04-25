"""
Tool handler implementations for document understanding server.

This module contains the implementation of all tools exposed by the document understanding server.
"""

import sys
from typing import Dict, List, Optional, Any, Union, cast

from pydantic import ValidationError
from .extractor import PDFExtractor
from .logging_config import get_logger

# Import response models
from .models import (
    MetadataResponse,
    MetadataResponseData,
    TextContentResponse,
    TextContentResponseData,
    SearchResponse,
    SearchResponseData,
    LayoutResponse,
    LayoutResponseData,
    SearchResult,
    Rect as RectModel,
    ImageExtractionResponse,
    ImageExtractionResponseData,
    ImageDescriptor,
    SimpleImageInfo,
    PageContent,
    TableExtractionResponse,
    TableExtractionResponseData,
    Table,
    LanguageDetectionResponse,
    LanguageDetectionResponseData,
    LanguageDetection,
    OutlineResponse,
    OutlineResponseData,
    PageLayout,
    WorkingDirectoryResponse,
    WorkingDirectoryResponseData,
)

# Initialize logger
logger = get_logger(__name__)

# Type alias for handler return types
ToolHandlerResult = Union[
    TextContentResponse,
    LayoutResponse,
    MetadataResponse,
    SearchResponse,
    ImageExtractionResponse,
    TableExtractionResponse,
    LanguageDetectionResponse,
    OutlineResponse,
    WorkingDirectoryResponse,
]

# Reference to the global extractor - will be set by server.py
_extractor: Optional[PDFExtractor] = None
_base_path: Optional[str] = None
_allow_any_path: bool = False


def initialize(
    extractor: PDFExtractor, base_path: Optional[str], allow_any_path: bool
) -> None:
    """Initialize the handlers module with global settings."""
    global _extractor, _base_path, _allow_any_path
    _extractor = extractor
    _base_path = base_path
    _allow_any_path = allow_any_path


def get_extractor() -> PDFExtractor:
    """Get the configured extractor instance."""
    if _extractor is None:
        # This should never happen as validation checks are already in place,
        # but provide a clear error message if it somehow does
        raise RuntimeError("Extractor not initialized - server setup is incomplete")
    return _extractor


def handle_extract_text(
    arguments: Dict[str, Any],
    validated_pdf_path: str,
    pages_str: Optional[str],
) -> TextContentResponse:
    """
    Handle extract_pdf_contents tool call.
    Extract text content from PDF pages with OCR support.
    """
    if validated_pdf_path is None:
        raise ValueError("PDF path cannot be None for extract_text operation")
    use_ocr = arguments.get("use_ocr", False)
    ocr_engine = arguments.get("ocr_engine", "tesseract")

    text_content_data = get_extractor().extract_content(
        pdf_path=validated_pdf_path,
        pages_str=pages_str,
        ocr_language=ocr_engine,
        force_ocr=use_ocr,
    )

    validated_pages = [
        PageContent(
            page_number=int(page_data.get("page") or 0),
            text=page_data.get("content") or "",
            error=None,
        )
        for page_data in text_content_data
    ]

    try:
        # Create the response data container
        response_data = TextContentResponseData(
            pages=validated_pages,
            ocr_languages_used=[ocr_engine] if use_ocr else None,
        )

        # Create the full response
        return TextContentResponse(
            status="success", message="Text extracted successfully", data=response_data
        )
    except ValidationError as e:
        logger.error(
            f"Error creating TextContentResponse: {e}",
            validated_pages=validated_pages,
        )
        raise ValueError(f"Failed to create text content response: {e}") from e


def handle_extract_layout(
    arguments: Dict[str, Any],
    validated_pdf_path: str,
    pages_str: Optional[str],
) -> LayoutResponse:
    """
    Handle extract_pdf_layout tool call.
    Extract layout information from PDF pages.
    """
    if validated_pdf_path is None:
        raise ValueError("PDF path cannot be None for extract_layout operation")
    include_images_arg = arguments.get("include_images", False)
    include_drawings_arg = arguments.get("include_drawings", False)
    detail_level_arg = arguments.get("detail_level")

    layout_data = get_extractor().extract_layout(
        validated_pdf_path,
        pages_str,
        include_images=include_images_arg,
        include_drawings=include_drawings_arg,
        detail_level=detail_level_arg,
    )

    try:
        validated_pages = [PageLayout(**page) for page in layout_data]
    except Exception as e:
        logger.error(
            f"Error validating page layout data from extractor: {e}",
            layout_data=layout_data,
        )
        raise ValueError(f"Extractor returned invalid layout data: {e}") from e

    try:
        # Create the response data container
        response_data = LayoutResponseData(
            layout=validated_pages,
            include_images=include_images_arg,
            include_drawings=include_drawings_arg,
        )

        # Create the full response
        return LayoutResponse(
            status="success",
            message="Layout extracted successfully",
            data=response_data,
        )
    except ValidationError as e:
        logger.error(
            f"Error creating LayoutResponse with validated pages: {e}",
            validated_pages=validated_pages,
        )
        raise ValueError(f"Failed to create layout response: {e}") from e


def handle_extract_metadata(
    arguments: Dict[str, Any],
    validated_pdf_path: str,
    pages_str: Optional[str],
) -> MetadataResponse:
    """
    Handle extract_pdf_metadata tool call.
    Extract metadata from a PDF file.
    """
    if validated_pdf_path is None:
        raise ValueError("PDF path cannot be None for extract_metadata operation")
    metadata = get_extractor().extract_metadata(validated_pdf_path)

    try:
        # Create the response data container
        response_data = MetadataResponseData(
            page_count=metadata.get("page_count", -1),
            metadata=metadata.get("metadata", {}),
            has_embedded_images=metadata.get("has_embedded_images"),
            has_vector_drawings=metadata.get("has_vector_drawings"),
        )

        # Create the full response
        return MetadataResponse(
            status="success",
            message="Metadata extracted successfully",
            data=response_data,
        )
    except ValidationError as e:
        logger.error(
            f"Error creating MetadataResponse: {e}",
            metadata=metadata,
        )
        raise ValueError(f"Failed to create metadata response: {e}") from e


def handle_search_text(
    arguments: Dict[str, Any],
    validated_pdf_path: str,
    pages_str: Optional[str],
) -> SearchResponse:
    """
    Handle search_pdf_text tool call.
    Search for text in a PDF and return locations.
    """
    if validated_pdf_path is None:
        raise ValueError("PDF path cannot be None for search_text operation")

    query = arguments.get("query", "")
    if not query:
        raise ValueError("Missing required argument: query")

    # Perform the search - note: case_sensitive is not supported by current PDFExtractor
    search_results = get_extractor().search_text(
        validated_pdf_path, query, pages_str=pages_str
    )

    # Transform results to model format
    search_result_models = []

    # Ensure search_results is a list
    if not isinstance(search_results, list):
        if isinstance(search_results, dict) and "results" in search_results:
            # Handle dict format with results key
            search_results = search_results["results"]
        else:
            # This is a fallback for unexpected formats
            logger.warning(f"Unexpected search results format: {type(search_results)}")
            if isinstance(search_results, str):
                # Handle string result - can't process this
                logger.error(f"Cannot process string search result: {search_results}")
                search_results = []
            else:
                # Try to convert to list
                search_results = [search_results]

    for result in search_results:
        try:
            if isinstance(result, str):
                logger.warning(f"Skipping string result: {result}")
                continue

            if isinstance(result, dict):
                page_num = result.get("page", 0)
                rect_data = result.get("rect", [0, 0, 0, 0])
            else:
                # Try to handle as object
                page_num = getattr(result, "page", 0)
                rect_data = getattr(result, "rect", [0, 0, 0, 0])

            # Create model from list - rect data comes as [x0, y0, x1, y1]
            if isinstance(rect_data, list) and len(rect_data) >= 4:
                rect_model = RectModel(
                    x0=rect_data[0], y0=rect_data[1], x1=rect_data[2], y1=rect_data[3]
                )
            elif isinstance(rect_data, dict):
                rect_model = RectModel(
                    x0=rect_data.get("x0", 0),
                    y0=rect_data.get("y0", 0),
                    x1=rect_data.get("x1", 0),
                    y1=rect_data.get("y1", 0),
                )
            else:
                # Fallback in case format changes
                rect_model = RectModel(x0=0, y0=0, x1=0, y1=0)

            search_result_models.append(SearchResult(page=page_num, rect=rect_model))
        except Exception as e:
            logger.warning(f"Error processing search result: {e}", result=result)
            continue

    try:
        # Create the response data container
        response_data = SearchResponseData(
            results=search_result_models,
            query=query,
            total_matches=len(search_result_models),
        )

        # Create the full response
        return SearchResponse(
            status="success",
            message=f"Found {len(search_result_models)} matches for '{query}'",
            data=response_data,
        )
    except ValidationError as e:
        logger.error(
            f"Error creating SearchResponse: {e}",
            results=search_result_models,
        )
        raise ValueError(f"Failed to create search response: {e}") from e


def handle_extract_images(
    arguments: Dict[str, Any],
    validated_pdf_path: str,
    pages_str: Optional[str],
) -> ImageExtractionResponse:
    """
    Handle extract_images tool call.
    Extract images from PDF pages and optionally save to files.
    """
    if validated_pdf_path is None:
        raise ValueError("PDF path cannot be None for extract_images operation")

    include_data = arguments.get("include_data", False)
    min_width = arguments.get("min_width")
    min_height = arguments.get("min_height")
    filter_bbox = arguments.get("filter_bbox")
    output_directory = arguments.get("output_directory")
    save_without_returning_data = arguments.get("save_without_returning_data", False)

    # If save_without_returning_data is True, we need to extract the image data
    # to save it to files, but we won't return it in the response
    extract_data = bool(
        include_data or (save_without_returning_data and output_directory)
    )

    image_data = get_extractor().extract_images(
        pdf_path=validated_pdf_path,
        pages_str=pages_str,
        include_data=extract_data,
        min_width=min_width,
        min_height=min_height,
        filter_bbox=filter_bbox,
        output_directory=output_directory,
        save_without_returning_data=save_without_returning_data,
    )

    # Convert dicts/objects to Pydantic models for validation/consistency
    validated_images: List[ImageDescriptor] = []
    for img_desc in image_data:
        try:
            if isinstance(img_desc, ImageDescriptor):
                validated_images.append(img_desc)
            elif isinstance(img_desc, SimpleImageInfo):
                # Find corresponding page number if possible, else default
                page_num = getattr(img_desc, "page_number", 1)
                validated_images.append(
                    ImageDescriptor(
                        page_number=page_num,
                        xref=img_desc.xref,
                        width=img_desc.width,
                        height=img_desc.height,
                        bbox=img_desc.bbox,
                        data=None,
                        format=None,
                    )
                )
            elif isinstance(img_desc, dict):
                # Find corresponding page number if possible, else default
                page_num = img_desc.get("page_number", 1)
                validated_images.append(
                    ImageDescriptor(
                        page_number=page_num,
                        **{k: v for k, v in img_desc.items() if k != "page_number"},
                    )
                )
            else:
                # If it's some other object type, attempt conversion if it has necessary attrs
                page_num = getattr(img_desc, "page_number", 1)
                validated_images.append(
                    ImageDescriptor(page_number=page_num, **img_desc.__dict__)
                )
        except Exception as img_err:
            logger.warning(
                f"Skipping invalid image descriptor: {img_err}", img_data=img_desc
            )

    try:
        # Create the response data container
        response_data = ImageExtractionResponseData(
            images=validated_images, include_data=include_data
        )

        # Create the full response
        return ImageExtractionResponse(
            status="success",
            message="Images extracted successfully",
            data=response_data,
        )
    except ValidationError as e:
        logger.error(
            f"Error creating ImageExtractionResponse: {e}",
            validated_images=validated_images,
        )
        raise ValueError(f"Failed to create image extraction response: {e}") from e


def handle_extract_tables(
    arguments: Dict[str, Any],
    validated_pdf_path: str,
    pages_str: Optional[str],
) -> TableExtractionResponse:
    """
    Handle extract_tables tool call.
    Extract tables from PDF pages.
    """
    if validated_pdf_path is None:
        raise ValueError("PDF path cannot be None for extract_tables operation")

    tables_data = get_extractor().extract_tables(validated_pdf_path, pages_str)

    validated_tables = [
        Table(
            page_number=tbl.get("page_number", -1),
            table_number=tbl.get("table_index_on_page", -1),
            data=tbl.get("data", []),
        )
        for tbl in tables_data
    ]

    try:
        # Create the response data container
        response_data = TableExtractionResponseData(tables=validated_tables)

        # Create the full response
        return TableExtractionResponse(
            status="success",
            message="Tables extracted successfully",
            data=response_data,
        )
    except ValidationError as e:
        logger.error(
            f"Error creating TableExtractionResponse: {e}",
            validated_tables=validated_tables,
        )
        raise ValueError(f"Failed to create table extraction response: {e}") from e


def handle_detect_language(
    arguments: Dict[str, Any],
    validated_pdf_path: str,
    pages_str: Optional[str],
) -> LanguageDetectionResponse:
    """
    Handle detect_language tool call.
    Detect the language(s) used in a PDF.
    """
    if validated_pdf_path is None:
        raise ValueError("PDF path cannot be None for detect_language operation")

    sample_size = arguments.get("sample_size")
    detect_result = get_extractor().detect_language(
        validated_pdf_path,
        pages_str,
        sample_size=sample_size if sample_size is not None else 2000,
    )

    validated_detections = [
        LanguageDetection(**det) for det in detect_result.get("detections", [])
    ]

    try:
        # Create the response data container
        response_data = LanguageDetectionResponseData(
            detections=validated_detections,
            text_sample_used=detect_result.get("text_sample_used", ""),
        )

        # Create the full response
        return LanguageDetectionResponse(
            status="success",
            message="Language detection completed successfully",
            data=response_data,
        )
    except ValidationError as e:
        logger.error(
            f"Error creating LanguageDetectionResponse: {e}",
            validated_detections=validated_detections,
        )
        raise ValueError(f"Failed to create language detection response: {e}") from e


def handle_extract_pdf_outline(
    arguments: Dict[str, Any],
    validated_pdf_path: str,
    pages_str: Optional[str],
) -> OutlineResponse:
    """
    Handle extract_pdf_outline tool call.
    Extract the document outline (table of contents).
    """
    if validated_pdf_path is None:
        raise ValueError("PDF path cannot be None for extract_pdf_outline operation")

    # pages_str is ignored for outline extraction
    logger.debug(f"Handling tool: extract_pdf_outline with path: {validated_pdf_path}")

    try:
        outline_data = get_extractor().extract_outline(validated_pdf_path)
        logger.debug("Outline extraction successful", outline_length=len(outline_data))

        # Create the response data container
        response_data = OutlineResponseData(outline=outline_data, image_url=None)

        # Create the full response
        return OutlineResponse(
            status="success",
            message="Outline extracted successfully",
            data=response_data,
        )
    except Exception as outline_exc:
        import traceback

        exc_traceback = traceback.format_exc()
        logger.error(
            f"Error during extractor.extract_outline call: {outline_exc}\nTraceback:\n{exc_traceback}",
            exc_info=False,
        )
        print(
            (
                f"ERROR [handle_call_tool -> handle_extract_pdf_outline]: "
                f"Error during extractor.extract_outline call: {outline_exc}\n"
                f"Traceback:\n{exc_traceback}"
            ),
            file=sys.stderr,
        )
        # Re-raise to be caught by the main handler in handle_call_tool
        raise


def handle_get_pdf_working_directory(
    arguments: Dict[str, Any],
    validated_pdf_path: Optional[str],
    pages_str: Optional[str],
) -> WorkingDirectoryResponse:
    """
    Handle get_pdf_working_directory tool call.
    Return the working directory for PDFs.
    """
    logger.debug("Handling tool: get_pdf_working_directory")

    try:
        if _allow_any_path:
            # Create the response data container
            response_data = WorkingDirectoryResponseData(
                working_directory=None, allow_any_path=True
            )

            # Create the full response
            return WorkingDirectoryResponse(
                status="success",
                message="Server configured to allow arbitrary paths.",
                data=response_data,
            )
        else:
            # Create the response data container
            response_data = WorkingDirectoryResponseData(
                working_directory=_base_path, allow_any_path=False
            )

            # Create the full response
            return WorkingDirectoryResponse(
                status="success", message=None, data=response_data
            )
    except ValidationError as e:
        logger.error(
            f"Error creating WorkingDirectoryResponse: {e}",
        )
        raise ValueError(f"Failed to create working directory response: {e}") from e
