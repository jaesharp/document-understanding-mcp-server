from PIL import Image
import fitz  # PyMuPDF
import re  # noqa: F401 - Used for parsing page ranges in other modules that import from here
import os  # Added
from typing import (  # noqa: F401 - Several unused types needed for derived classes/type hints
    List,
    Optional,
    Set,  # noqa: F401 - Used for type annotations in derived classes
    Callable,
    Any,
    Tuple,  # noqa: F401 - Used for return type annotations in derived classes
    Dict,
    Literal,  # noqa: F401 - Used for type annotations in derived classes
    TYPE_CHECKING,
    TypeVar,  # noqa: F401 - Used for generic type definitions in derived classes
    Union,  # noqa: F401 - Used for type annotations in derived classes
    TypeAlias,  # noqa: F401 - Used for type alias definitions in this module
)  # Added TYPE_CHECKING and type alias support

# Import stub types for PyMuPDF objects
from ..logging_config import get_logger
import base64  # noqa: F401 - Used for image encoding in derived modules
from ..models import (  # noqa: F401 - Models used in derived modules imported from here
    # These model imports are used in derived modules that import from this module
    # They are kept here to provide a single import point for all PDF extraction functionality
    MetadataResponse,  # noqa: F401 - Used in metadata_extraction.py
    TextContentResponse,  # noqa: F401 - Used in content_extraction.py
    SearchResponse,  # noqa: F401 - Used in text_search.py
    LayoutResponse,  # noqa: F401 - Used in layout_extraction.py
    SearchResult,  # noqa: F401 - Used in text_search.py
    Rect as RectModel,  # noqa: F401 - Used for type conversions in derived modules
    ImageExtractionResponse,  # noqa: F401 - Used in image_extraction.py
    ImageDescriptor,  # noqa: F401 - Used in image_extraction.py
    TableExtractionResponse,  # noqa: F401 - Used in table_extraction.py
    Table,  # noqa: F401 - Used in table_extraction.py
    LanguageDetectionResponse,  # noqa: F401 - Used in language_detection.py
    LanguageDetection,  # noqa: F401 - Used in language_detection.py
    OutlineResponse,  # noqa: F401 - Used in outline_extraction.py
    OutlineItem,  # noqa: F401 - Used in outline_extraction.py
    PageLayout,  # noqa: F401 - Used in layout_extraction.py
    TextBlock,  # noqa: F401 - Used in layout_extraction.py
    TextLine,  # noqa: F401 - Used in layout_extraction.py
    TextSpan,  # noqa: F401 - Used in layout_extraction.py
    SimpleImageInfo,  # noqa: F401 - Used in layout_extraction.py
    Point,  # noqa: F401 - Used for geometric operations in derived modules
    Rect,  # noqa: F401 - Used for geometric operations in derived modules
)
from ..exceptions import (
    PDFExtractionError,
    PDFPasswordError,
)
import tabula  # noqa: F401 - Used in table_extraction.py
import pandas as pd  # noqa: F401 - Used for DataFrame operations in table_extraction.py
from langdetect import DetectorFactory
import math  # noqa: F401 - Used for distance calculations in derived modules
import structlog
import functools  # Added for lru_cache

# Import the base class
from .base import Extractor  # Should be correct now

# Import the moved function with its new name
from .image_extraction import _extract_images_impl  # Corrected import name

# Import the new layout extraction implementation
from .layout_extraction import _extract_layout_impl  # Should be correct now

# Import the new page parsing implementation
from .page_parsing import _parse_pages_impl  # Should be correct now

# Import the new content extraction implementation
from .content_extraction import _extract_content_impl  # Should be correct now

# Import the new metadata extraction implementation
from .metadata_extraction import _extract_metadata_impl  # Should be correct now

# Import the new text search implementation
from .text_search import _search_text_impl  # Should be correct now

# Import the new table extraction implementation
from .table_extraction import _extract_tables_impl  # Should be correct now

# Import the new language detection implementation
from .language_detection import _detect_language_impl  # Should be correct now

# Import the new outline extraction implementation
from .outline_extraction import _extract_outline_impl  # Should be correct now

# Attempt to import TesseractError, handle if pytesseract not installed
try:
    from pytesseract import TesseractError as TesseractErrorType
except ImportError:

    class TesseractErrorType(Exception):  # type: ignore
        "Dummy exception if pytesseract is not installed."


# Conditional import for type hinting
if TYPE_CHECKING:
    pass

# Use configured logger
logger = get_logger(__name__)

# Hardcoded default threshold, can be overridden by context later
DEFAULT_MIN_TEXT_LENGTH_FOR_NON_OCR = 20

# Type hints using fitz types are imported from fitz_stubs
# More specific type hint for the OCR runner callable
# Takes a PIL Image and a language string keyword argument
OCRRunnerCallable = Callable[[Image.Image, str], str]
ImageType = Any  # Placeholder for PIL Image type if needed elsewhere

# Ensure consistent language detection results for short/ambiguous text
DetectorFactory.seed = 0

# --- Geometry Helper Functions ---
# REMOVED - Moved to geometry_helpers.py
# def calculate_center(bbox: List[float]) -> Tuple[float, float]: ...
# def calculate_distance(bbox1: List[float], bbox2: List[float]) -> float: ...
# def get_relative_position(target_bbox: List[float], element_bbox: List[float]) -> str: ...

# ------------------------------


class PDFExtractor(Extractor):  # Revert class name and inheritance
    """
    Provides methods to extract various types of information from PDF files.
    Relies on PyMuPDF (fitz) for core PDF parsing and optionally Tesseract for OCR.
    Delegates implementation details to separate modules.
    """

    # Define type for OCR runner
    OCRRunnerType = Callable[[Any, str], str]

    # Define instance variables with type annotations
    _file_exists: Any
    _open_pdf: Any
    _capabilities: Dict[str, bool]
    _ocr_runner: Optional[OCRRunnerType]

    def _open_pdf_document(
        self, pdf_path: str, password: Optional[str] = None
    ) -> Any:  # Return Any instead of PDFDocument to avoid type issues
        """Helper to open PDF with password handling. Returns an open document.
        Caller is responsible for closing the document.
        """
        doc = None  # Define doc outside try block
        try:
            # Open the document first using the injected opener
            doc = self._open_pdf(pdf_path)

            # Ensure doc is not None before proceeding
            if doc is None:
                raise PDFExtractionError(f"Failed to open PDF file: {pdf_path}")

            # Now, handle authentication if a password is required or provided
            # needs_pass can be a function or a property, so we need to check both cases
            needs_password = False
            if hasattr(doc, "needs_pass"):
                if callable(getattr(doc, "needs_pass", None)):
                    needs_password = bool(doc.needs_pass())
                else:
                    needs_password = bool(doc.needs_pass)

                if needs_password:
                    if not password:
                        raise PDFPasswordError(
                            f"PDF file requires a password but none was provided: {pdf_path}"
                        )
                    else:
                        # Authenticate with the provided password
                        if hasattr(doc, "authenticate"):
                            authenticated = doc.authenticate(password)
                            if not authenticated:
                                raise PDFPasswordError(
                                    f"Incorrect password provided for PDF: {pdf_path}"
                                )
                        else:
                            raise PDFPasswordError(
                                f"PDF requires a password but authentication method is not available: {pdf_path}"
                            )
                elif password:
                    # Password provided but not needed - log a warning
                    self.log.warning(
                        f"Password provided for PDF '{pdf_path}' but it is not encrypted."
                    )

            self.log.debug(f"Successfully opened and validated PDF: {pdf_path}")
            return doc  # Return the open document

        except PDFPasswordError as e:
            # Close doc if opened before password error
            if doc:
                doc.close()
            raise e
        except RuntimeError as e:
            if doc:
                doc.close()
            err_msg = str(e).lower()
            if "encrypted pdf" in err_msg or "password" in err_msg:
                raise PDFPasswordError(
                    f"PDF requires a password or provided password was incorrect: {pdf_path}"
                ) from e
            else:
                raise PDFExtractionError(
                    f"Runtime error processing PDF '{pdf_path}': {e}"
                ) from e
        except Exception as e:
            if doc:
                doc.close()
            raise PDFExtractionError(
                f"Failed to open PDF file '{pdf_path}': {e}"
            ) from e

    # --- Helper Function for Outline Parsing ---
    # def _parse_toc_recursive(self, toc_list: list, current_level: int = 1) -> List[OutlineItem]: ...

    def __init__(
        self,
        default_ocr_language: str = "eng",
        file_exists_checker: Callable[[str], bool] = os.path.exists,
        pdf_opener: Callable[[str], Any] = fitz.open,
        capabilities: Optional[Dict[str, bool]] = None,
        ocr_runner: Optional[Any] = None,  # Accept pre-configured OCR runner
    ):
        """
        Initializes the PDFExtractor.

        Args:
            file_exists_checker: Function to check if a file path exists.
            pdf_opener: Function to open a PDF file (e.g., fitz.open).
            capabilities: Dictionary indicating enabled features (e.g., {'tesseract_ocr': True}).
            ocr_runner: An optional pre-configured OCR runner instance.
        """
        # Store the file existence checker and PDF opener functions
        # Use a wrapper function to avoid type issues
        self._file_exists = lambda path: file_exists_checker(path)
        self._open_pdf = lambda path: pdf_opener(path)
        # Store capabilities in a private attribute, defaulting OCR to False
        self._capabilities = capabilities if capabilities is not None else {}
        if "tesseract_ocr" not in self._capabilities:
            self._capabilities["tesseract_ocr"] = False  # Default OCR off

        self.log = structlog.get_logger(self.__class__.__name__)

        # Use pytesseract if available and capability is True, else disable OCR runner
        self.ocr_enabled = self._capabilities.get("tesseract_ocr", False)

        # Initialize OCR runner variable
        self._ocr_runner: Optional[PDFExtractor.OCRRunnerType] = None

        if self.ocr_enabled and ocr_runner is None:
            try:
                import pytesseract

                # Use the class-level OCRRunnerType
                self._ocr_runner = lambda img, lang: pytesseract.image_to_string(
                    img, lang=lang
                )
                logger.debug("Tesseract OCR runner initialized.")
            except ImportError:
                logger.warning(
                    "pytesseract or Pillow not installed, disabling OCR capability "
                    "even though Tesseract might be present."
                )
                self.ocr_enabled = False  # Disable if Python deps missing
                # ALSO update the capabilities dict to reflect reality
                self._capabilities["tesseract_ocr"] = False
        elif ocr_runner is not None:
            # Allow injecting a custom OCR runner (mostly for testing)
            logger.debug("Using provided custom OCR runner.")
            self._ocr_runner = ocr_runner
            # Assume OCR is enabled if a runner is provided, regardless of tesseract check
            self.ocr_enabled = True
        else:
            # No runner provided and capability is false or Python deps missing
            logger.debug("OCR runner is disabled.")

        self.log.debug("PDFExtractor initialized", capabilities=self._capabilities)

    @property
    def capabilities(self) -> Dict[str, bool]:
        """Returns the configured capabilities of the extractor."""
        # Return the private attribute
        return self._capabilities

    def parse_pages(self, pages_str: Optional[str], total_pages: int) -> List[int]:
        """
        Parses a user-provided page string (1-based indexing) into a sorted list
        of 0-based page indices using the implementation function.

        Supports:
        - Comma-separated values (e.g., "1, 3, 5")
        - Ranges (e.g., "1-3", "5-7")
        - Negative indices (e.g., "-1" for last, "-2" for second last)
        - Combinations (e.g., "1, 3-5, -1")

        Args:
            pages_str: The string representation of pages to parse, or None/empty for all pages.
            total_pages: The total number of pages in the PDF document.

        Returns:
            A sorted list of unique 0-based page indices.

        Raises:
            ValueError: If the page string format is invalid or specifies invalid pages.
        """
        # Delegate to the implementation function
        return _parse_pages_impl(pages_str, total_pages)

    def extract_content(
        self,
        pdf_path: str,
        pages_str: Optional[str],
        ocr_language: Optional[str] = None,
        force_ocr: bool = False,
        password: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Extracts text content from specified pages by calling the implementation function.
        """
        # Delegate to the implementation function
        return _extract_content_impl(
            self,  # Pass instance
            pdf_path=pdf_path,
            pages_str=pages_str,
            ocr_language=ocr_language,
            force_ocr=force_ocr,
            password=password,
        )

    def extract_metadata(
        self, pdf_path: str, password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extracts metadata and basic structural info (page count, image/drawing presence).

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            A dictionary containing page_count, metadata, and flags.
        """
        # Delegate to the implementation function
        return _extract_metadata_impl(self, pdf_path, password=password)

    def search_text(
        self,
        pdf_path: str,
        query: str,
        pages_str: Optional[str],
        password: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Searches for text within specified pages by calling the implementation function.
        """
        # Delegate to the implementation function
        return _search_text_impl(
            self, pdf_path=pdf_path, query=query, pages_str=pages_str, password=password
        )

    @functools.lru_cache(maxsize=128)  # Keep the cache decorator here
    def extract_layout(
        self,
        pdf_path: str,
        pages_str: Optional[str],
        include_images: bool = False,
        include_drawings: bool = False,
        detail_level: Optional[str] = None,
        password: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Extracts layout information by calling the implementation function."""
        # Log entry can be simple or include more details based on args
        self.log.info(f"Extracting layout for: {pdf_path}, pages: {pages_str or 'all'}")
        # Delegate the actual work to the implementation function
        return _extract_layout_impl(
            self,  # Pass the instance itself
            pdf_path=pdf_path,
            pages_str=pages_str,
            include_images=include_images,
            include_drawings=include_drawings,
            detail_level=detail_level,
            password=password,
        )

    def extract_images(
        self,
        pdf_path: str,
        pages_str: Optional[str],
        include_data: bool = False,
        min_width: Optional[int] = None,
        min_height: Optional[int] = None,
        filter_bbox: Optional[List[float]] = None,
        password: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Extracts image information by calling the implementation function."""
        self.log.info(f"Extracting images for: {pdf_path}, pages: {pages_str or 'all'}")
        # Delegate to implementation function, passing all arguments
        return _extract_images_impl(
            self,
            pdf_path=pdf_path,
            pages_str=pages_str,
            include_data=include_data,
            min_width=min_width,
            min_height=min_height,
            filter_bbox=filter_bbox,
            password=password,
        )

    def extract_tables(
        self, pdf_path: str, pages_spec: Optional[str], password: Optional[str] = None
    ) -> List[dict]:
        """
        Extracts tables from specified pages by calling the implementation function.
        Accepts an optional password.
        """
        self.log.info(
            f"Extracting tables for: {pdf_path}, pages: {pages_spec or 'all'}"
        )
        # Delegate to implementation function, passing the password
        return _extract_tables_impl(
            self,
            pdf_path=pdf_path,
            pages_spec=pages_spec,
            password=password,  # Pass the password here
        )

    def detect_language(
        self,
        pdf_path: str,
        pages_str: Optional[str],
        sample_size: Optional[int] = 2000,
        password: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Detects the language(s) of the text content by calling the implementation function.
        """
        # Delegate to the implementation function
        return _detect_language_impl(
            self,
            pdf_path=pdf_path,
            pages_str=pages_str,
            sample_size=sample_size,
            password=password,
        )

    # --- New Outline Extraction Method ---
    def extract_outline(
        self, pdf_path: str, password: Optional[str] = None
    ) -> List[OutlineItem]:
        """Extracts the document outline (TOC/Bookmarks), handling passwords."""
        self.log.info(f"Extracting outline for: {pdf_path}")
        # Pass the password argument
        return _extract_outline_impl(self, pdf_path, password=password)

    # --- Core Helper Methods ---

    def is_ocr_available(self) -> bool:
        """Check if OCR capability is enabled and potentially usable."""
        # Basic check based on initialization capabilities and if runner was initialized
        is_enabled = self.capabilities.get("tesseract_ocr", False)
        ocr_runner_exists = (
            hasattr(self, "_ocr_runner") and self._ocr_runner is not None
        )
        # Log the check result for debugging
        # self.log.debug(f"OCR available check: enabled={is_enabled}, runner_exists={ocr_runner_exists}")
        return (
            is_enabled and ocr_runner_exists
        )  # Return True only if enabled AND runner exists

    def check_file_exists(self, path: str) -> bool:
        """Wrapper for file existence check."""
        result = self._file_exists(path)
        return bool(result)  # Ensure boolean return type
