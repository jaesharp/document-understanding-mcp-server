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
                "Path relative to working dir, or absolute if allowed."
            )
        elif field_name == "pages":
            field_desc["description"] = (
                "Optional: Page spec (1-based, ranges, neg indices). Default=all."
            )
        elif field_name == "password":
            field_desc["description"] = "Optional: Password for encrypted PDFs."
        elif field_name == "query":
            field_desc["description"] = "The text to search for (case-sensitive)"
        elif field_name == "include_data":
            field_desc["description"] = (
                "If true, include base64 image data (large!). Default=false."
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
