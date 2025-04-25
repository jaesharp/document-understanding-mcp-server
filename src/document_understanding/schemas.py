"""
Schema definitions for tool input parameters.

This module contains TypedDict classes for all tool input schemas.
"""

from typing import Dict, List, TypedDict, Any, NotRequired


# Common parameter definitions as TypedDict base classes
class PDFPathParam(TypedDict):
    """Parameter for PDF path"""

    pdf_path: str  # Path relative to working dir, or absolute if allowed


class PagesParam(TypedDict):
    """Parameter for page specification"""

    pages: NotRequired[str]  # Page spec (1-based, ranges, neg indices)


class PasswordParam(TypedDict):
    """Parameter for PDF password"""

    password: NotRequired[str]  # Password for encrypted PDFs


# Tool-specific input schemas
class ExtractTextSchema(PDFPathParam, PagesParam, PasswordParam):
    """Schema for extract_pdf_contents tool"""

    ocr_language: NotRequired[str]  # OCR language(s) (e.g., 'eng', 'fra+eng')


class ExtractLayoutSchema(PDFPathParam, PagesParam, PasswordParam):
    """Schema for extract_pdf_layout tool"""

    include_images: NotRequired[bool]  # Include image info
    include_drawings: NotRequired[bool]  # Include vector drawing info
    detail_level: NotRequired[str]  # Text detail level ('blocks', 'lines', 'words')


class ExtractMetadataSchema(PDFPathParam, PasswordParam):
    """Schema for extract_pdf_metadata tool"""

    pass


class SearchTextSchema(PDFPathParam, PagesParam, PasswordParam):
    """Schema for search_pdf_text tool"""

    query: str  # The text to search for (case-sensitive)


class ExtractImagesSchema(PDFPathParam, PagesParam, PasswordParam):
    """Schema for extract_images tool"""

    include_data: NotRequired[bool]  # Include base64 image data
    min_width: NotRequired[int]  # Minimum image width to include
    min_height: NotRequired[int]  # Minimum image height to include
    filter_bbox: NotRequired[List[float]]  # Region filter [x0, y0, x1, y1]
    output_directory: NotRequired[
        str
    ]  # Directory to save extracted images (requires ENABLE_SAVE_IMAGES_TO_FILES=true)
    save_without_returning_data: NotRequired[
        bool
    ]  # Save images to files without returning base64 data in response


class ExtractTablesSchema(PDFPathParam, PagesParam, PasswordParam):
    """Schema for extract_tables tool"""

    pass


class DetectLanguageSchema(PDFPathParam, PasswordParam):
    """Schema for detect_language tool"""

    pages: NotRequired[str]  # Page spec for sampling
    sample_size: NotRequired[int]  # Max characters to sample


class ExtractOutlineSchema(PDFPathParam, PasswordParam):
    """Schema for extract_pdf_outline tool"""

    pass


class GetWorkingDirectorySchema(TypedDict):
    """Schema for get_pdf_working_directory tool"""

    pass


# Dictionary to map tool names to their schema classes
SCHEMA_CLASSES = {
    "extract_pdf_contents": ExtractTextSchema,
    "extract_pdf_layout": ExtractLayoutSchema,
    "extract_pdf_metadata": ExtractMetadataSchema,
    "search_pdf_text": SearchTextSchema,
    "extract_images": ExtractImagesSchema,
    "extract_tables": ExtractTablesSchema,
    "detect_language": DetectLanguageSchema,
    "extract_pdf_outline": ExtractOutlineSchema,
    "get_pdf_working_directory": GetWorkingDirectorySchema,
}


# Function to generate JSON schema dictionaries for tool registration
def get_schema_dict(tool_name: str) -> Dict[str, Any]:
    """
    Convert a TypedDict schema to a JSON schema dictionary for tool registration.

    Args:
        tool_name: The name of the tool to get schema for

    Returns:
        A dictionary with the JSON schema format for the tool
    """
    schema_class = SCHEMA_CLASSES.get(tool_name)
    if not schema_class:
        return {}

    # Get annotations and required fields from the TypedDict
    annotations = getattr(schema_class, "__annotations__", {})
    required_fields = []

    properties = {}
    for field_name, field_type in annotations.items():
        field_desc = {
            "type": _python_type_to_json_type(field_type),
        }

        # Add descriptions
        if field_name == "pdf_path":
            field_desc["description"] = (
                "Path relative to working dir, or absolute if allowed. Use get_pdf_working_directory tool to find the base directory."
            )
        elif field_name == "pages":
            field_desc["description"] = (
                "Optional: Page spec (1-based, ranges, neg indices). Examples: '1,3,5' for specific pages, '1-5' for range, '-1' for last page. Default=all. "
                "IMPORTANT: For large documents, request small batches of pages (5-10 at a time) to avoid overwhelming your context window."
            )
        elif field_name == "password":
            field_desc["description"] = (
                "Optional: Password for encrypted PDFs. Only needed if the PDF is password-protected."
            )
        elif field_name == "query":
            field_desc["description"] = (
                "The text to search for (case-sensitive). Use specific, unique phrases for best results."
            )
        elif field_name == "include_data":
            field_desc["description"] = (
                "If true, include base64 image data (large!). Default=false. Only set to true when you need the actual image content. "
                "For most cases, prefer using output_directory with save_without_returning_data=true to avoid overwhelming your context window."
            )
        elif field_name == "output_directory":
            field_desc["description"] = (
                "Directory to save extracted images to. Requires ENABLE_SAVE_IMAGES_TO_FILES=true environment variable. "
                "Use this instead of include_data for large documents with many images. "
                "After saving images, use image understanding tools on the saved files for analysis. "
                "When analyzing saved images, provide relevant document context from surrounding text, captions, and references "
                "to help the vision model accurately interpret the image content."
            )
        elif field_name == "save_without_returning_data":
            field_desc["description"] = (
                "If true, save images to files without returning base64 data in response. Default=false. "
                "Use with output_directory for efficient image extraction. "
                "RECOMMENDED: Set to true when extracting images for analysis with image understanding tools."
            )
        elif field_name == "ocr_language":
            field_desc["description"] = (
                "Language code(s) for OCR, e.g., 'eng' for English, 'fra+eng' for French and English. Use detect_language tool first if unsure."
            )
        elif field_name == "min_width":
            field_desc["description"] = (
                "Minimum image width in pixels to include in results. Use to filter out small icons or decorations."
            )
        elif field_name == "min_height":
            field_desc["description"] = (
                "Minimum image height in pixels to include in results. Use to filter out small icons or decorations."
            )
        elif field_name == "filter_bbox":
            field_desc["description"] = (
                "Optional region filter [x0, y0, x1, y1] to only extract images within this area of the page."
            )
        elif field_name == "detail_level":
            field_desc["description"] = (
                "Level of detail for text extraction: 'blocks', 'lines', or 'words'. More detail means larger output. "
                "Use 'blocks' for document structure overview (headings, paragraphs), 'lines' for moderate detail, "
                "and 'words' only when precise word positioning is needed. 'blocks' is recommended for initial document analysis."
            )
        elif field_name == "include_images":
            field_desc["description"] = (
                "If true, include image placement information in layout results. Default=false."
            )
        elif field_name == "include_drawings":
            field_desc["description"] = (
                "If true, include vector drawing information in layout results. Default=false."
            )
        elif field_name == "sample_size":
            field_desc["description"] = (
                "Maximum number of characters to sample for language detection. Larger values may be more accurate but slower."
            )

        properties[field_name] = field_desc

        # Check if field is required (not a NotRequired type)
        if "NotRequired" not in str(field_type):
            required_fields.append(field_name)

    # Build the JSON schema
    json_schema = {
        "type": "object",
        "properties": properties,
    }

    if required_fields:
        json_schema["required"] = required_fields

    return json_schema


def _python_type_to_json_type(python_type: Any) -> str:
    """Convert Python type annotation to JSON schema type"""
    type_str = str(python_type)

    if "str" in type_str:
        return "string"
    elif "int" in type_str:
        return "integer"
    elif "float" in type_str:
        return "number"
    elif "bool" in type_str:
        return "boolean"
    elif "List" in type_str or "list" in type_str:
        return "array"
    elif "Dict" in type_str or "dict" in type_str:
        return "object"
    elif "Optional" in type_str:
        # For Optional types, we just return the base type
        # JSON Schema will handle nullability separately
        inner_type = type_str.split("[")[1].split("]")[0]
        return _python_type_to_json_type(inner_type)
    elif "Union" in type_str:
        # For Union types, we take the first non-None type
        # This is a simplification - proper handling would require a more complex schema
        inner_types = type_str.split("[")[1].split("]")[0].split(",")
        for inner_type in inner_types:
            if "None" not in inner_type:
                return _python_type_to_json_type(inner_type)

    # Default to string if we can't determine
    return "string"
