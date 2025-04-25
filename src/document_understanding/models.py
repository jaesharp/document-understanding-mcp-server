from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal, Any, TypeVar, Generic
from datetime import datetime
from pydantic import field_serializer

# Versioning and standard response fields
API_VERSION = "1.0.0"


class Point(BaseModel):
    x: float
    y: float


class Rect(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class TextSpan(BaseModel):
    size: float
    flags: int
    font: str
    color: int
    ascender: float
    descender: float
    text: str
    origin: Point
    bbox: Rect


class TextLine(BaseModel):
    spans: List[TextSpan]
    wmode: int
    dir: Point  # Tuple in PyMuPDF, using Point for structure
    bbox: Rect


class TextBlock(BaseModel):
    number: int
    type: int
    bbox: Rect
    lines: List[TextLine]


class DrawingRect(BaseModel):
    rect: Rect
    color: Optional[List[float]] = None
    fill: Optional[List[float]] = None
    width: float = 1.0
    closePath: bool = False
    # Add other common drawing attributes as needed
    # drawing_type: str # 'rect', 'line', 'curve', etc. - PyMuPDF structure might vary


class SimpleImageInfo(BaseModel):
    """Basic info about an image for layout context."""

    xref: int
    bbox: Optional[Rect]
    width: int
    height: int


# Define generic type for response data
T = TypeVar("T")


class BaseToolResponse(BaseModel, Generic[T]):
    """
    Standard base response model for all tool responses.

    This provides a consistent structure for all API responses, including
    metadata that can be useful for debugging and tracking.
    """

    status: Literal["success", "error"] = "success"
    message: Optional[str] = Field(
        None, description="Optional message, typically used for errors"
    )

    # Metadata fields
    api_version: str = Field(default=API_VERSION, description="API version")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when response was generated",
    )

    # Generic data field for specific response types
    data: Optional[T] = None

    # Error details when status is "error" - with default values
    error_code: Optional[str] = Field(
        default=None, description="Error code for programmatic handling"
    )
    error_details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional structured error information"
    )

    @field_serializer("timestamp")
    def serialize_datetime(self, dt: datetime):
        return dt.isoformat() + "Z"  # ISO 8601 format with UTC indicator


# Response data models
class MetadataResponseData(BaseModel):
    """Data container for metadata response"""

    page_count: int = Field(..., description="Total number of pages in the document.")
    metadata: Dict[str, Optional[str]] = Field(
        ..., description="Standard PDF metadata fields."
    )
    # Add flags for detected content types
    has_embedded_images: Optional[bool] = Field(
        None, description="Heuristic flag indicating if raster images were found."
    )
    has_vector_drawings: Optional[bool] = Field(
        None, description="Heuristic flag indicating if vector drawings were found."
    )


class MetadataResponse(BaseToolResponse[MetadataResponseData]):
    """Response for metadata extraction"""

    data: MetadataResponseData


# Define the structure for individual page content
class PageContent(BaseModel):
    page_number: int = Field(..., description="1-based page number.")
    text: str = Field(..., description="Extracted text content of the page.")
    error: Optional[str] = Field(
        None, description="Error message if extraction failed for this page."
    )


class TextContentResponseData(BaseModel):
    """Data container for text content response"""

    pages: List[PageContent] = Field(
        ..., description="List of content extracted from each page."
    )
    ocr_languages_used: Optional[List[str]] = Field(
        None, description="Languages used by OCR, if any"
    )


class TextContentResponse(BaseToolResponse[TextContentResponseData]):
    """Response for text content extraction"""

    data: TextContentResponseData


class SearchResult(BaseModel):
    page: int = Field(..., description="1-based page number")
    rect: Rect = Field(..., description="Bounding box of the found text")


class SearchResponseData(BaseModel):
    """Data container for search response"""

    results: List[SearchResult]
    query: str = Field(..., description="The search query that was used")
    total_matches: int = Field(..., description="Total number of matches found")


class SearchResponse(BaseToolResponse[SearchResponseData]):
    """Response for text search"""

    data: SearchResponseData


class PageLayout(BaseModel):
    page_number: int = Field(..., description="1-based page number")
    text_blocks: List[TextBlock] = Field(default_factory=list)
    drawings: List[Dict] = Field(
        default_factory=list, description="Raw drawing dicts from PyMuPDF for now"
    )  # Keep flexible for now
    images: List[SimpleImageInfo] = Field(
        default_factory=list,
        description="Bounding boxes and refs for raster images on the page.",
    )
    error: Optional[str] = None


class LayoutResponseData(BaseModel):
    """Data container for layout response"""

    layout: List[PageLayout]
    include_images: bool = Field(
        ..., description="Whether images were included in extraction"
    )
    include_drawings: bool = Field(
        ..., description="Whether drawings were included in extraction"
    )


class LayoutResponse(BaseToolResponse[LayoutResponseData]):
    """Response for layout extraction"""

    data: LayoutResponseData


class ImageDescriptor(BaseModel):
    page_number: int = Field(
        ..., description="1-based page number where the image was found."
    )
    xref: int = Field(..., description="Internal PDF object reference number.")
    width: int
    height: int
    bbox: Optional[Rect] = Field(
        None, description="Bounding box on the page (may be None if detection fails)."
    )
    # Optional base64 data
    data: Optional[str] = Field(
        None,
        description="Base64 encoded image data (if requested). Recommended format is PNG.",
    )
    format: Optional[str] = Field(
        None, description="Image format (e.g., png, jpeg) if data is included."
    )
    file_path: Optional[str] = Field(
        None,
        description="Path to saved image file (if output_directory was specified and ENABLE_SAVE_IMAGES_TO_FILES=true).",
    )


class ImageExtractionResponseData(BaseModel):
    """Data container for image extraction response"""

    images: List[ImageDescriptor]
    include_data: bool = Field(
        ..., description="Whether image data was included in extraction"
    )


class ImageExtractionResponse(BaseToolResponse[ImageExtractionResponseData]):
    """Response for image extraction"""

    data: ImageExtractionResponseData


class Table(BaseModel):
    """Represents a single table extracted from a page."""

    page_number: int
    # table_index_on_page: int # Renaming to match what handle_call_tool provides
    table_number: int  # Renamed from table_index_on_page for clarity
    bbox: Optional[List[float]] = None  # Optional: Bounding box [x0, y0, x1, y1]
    data: List[List[Optional[str]]]


class TableExtractionResponseData(BaseModel):
    """Data container for table extraction response"""

    tables: List[Table]


class TableExtractionResponse(BaseToolResponse[TableExtractionResponseData]):
    """Response for table extraction"""

    data: TableExtractionResponseData


class LanguageDetection(BaseModel):
    language_code: str = Field(
        ..., description="Detected language code (e.g., 'en', 'fr')."
    )
    confidence: float = Field(
        ..., description="Confidence score of the detection (0.0 to 1.0)."
    )


class LanguageDetectionResponseData(BaseModel):
    """Data container for language detection response"""

    detections: List[LanguageDetection] = Field(
        ..., description="List of detected languages and confidences."
    )
    text_sample_used: str = Field(
        ..., description="The text sample used for detection."
    )


class LanguageDetectionResponse(BaseToolResponse[LanguageDetectionResponseData]):
    """Response for language detection"""

    data: LanguageDetectionResponseData


# --- Outline/TOC Extraction Models ---


class OutlineItem(BaseModel):
    """Represents a single item in the PDF outline (TOC/Bookmark)."""

    title: str
    level: int  # Hierarchy level (starting from 1)
    page_number: int  # 1-based page number the item points to
    children: List["OutlineItem"] = Field(default_factory=list)  # Nested children items


# Required for forward references in Pydantic v2
OutlineItem.model_rebuild()


class OutlineResponseData(BaseModel):
    """Data container for outline response"""

    outline: List[OutlineItem] = Field(default_factory=list)
    image_url: Optional[str] = None


class OutlineResponse(BaseToolResponse[OutlineResponseData]):
    """Response for outline extraction"""

    data: OutlineResponseData


# === Working Directory Response Model ===
class WorkingDirectoryResponseData(BaseModel):
    """Data container for working directory response"""

    working_directory: Optional[str]
    allow_any_path: bool = Field(..., description="Whether any path is allowed")


class WorkingDirectoryResponse(BaseToolResponse[WorkingDirectoryResponseData]):
    """Response for working directory tool"""

    data: WorkingDirectoryResponseData


# Error response
class ErrorResponse(BaseToolResponse):
    """Standard error response"""

    status: Literal["error"] = "error"
    error_code: str
    message: str
