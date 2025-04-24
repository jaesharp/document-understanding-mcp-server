# src/document_understanding/extractor/base.py
import abc
from typing import List, Dict, Any, Optional

# Forward reference for OutlineItem if needed, or import later
# from ..models import OutlineItem # Avoid circular import if possible


class Extractor(abc.ABC):
    """Abstract Base Class defining the interface for document extractors."""

    @property
    @abc.abstractmethod
    def capabilities(self) -> Dict[str, bool]:
        """Returns a dictionary of the extractor's capabilities."""

    @abc.abstractmethod
    def parse_pages(self, pages_str: Optional[str], total_pages: int) -> List[int]:
        """
        Parses a user-provided page string (1-based indexing) into a sorted list
        of 0-based page indices.
        """

    @abc.abstractmethod
    def extract_content(
        self,
        pdf_path: str,
        pages_str: Optional[str],
        ocr_language: Optional[str] = "eng",
        force_ocr: bool = False,
    ) -> List[Dict[str, Any]]:
        """Extracts text content from specified pages."""

    @abc.abstractmethod
    def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """Extracts metadata from the document."""

    @abc.abstractmethod
    def search_text(
        self, pdf_path: str, query: str, pages_str: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Searches for text within specified pages."""

    @abc.abstractmethod
    def extract_layout(
        self,
        pdf_path: str,
        pages_str: Optional[str],
        include_images: bool = False,
        include_drawings: bool = False,
        detail_level: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Extracts detailed layout information."""

    @abc.abstractmethod
    def extract_images(
        self,
        pdf_path: str,
        pages_str: Optional[str],
        include_data: bool = False,
        min_width: Optional[int] = None,
        min_height: Optional[int] = None,
        filter_bbox: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """Extracts image information."""

    @abc.abstractmethod
    def extract_tables(
        self,
        pdf_path: str,
        pages_spec: Optional[str],  # Note: kept original name for consistency here
    ) -> List[Dict[str, Any]]:
        """Extracts tables from specified pages."""

    @abc.abstractmethod
    def detect_language(
        self, pdf_path: str, pages_str: Optional[str], sample_size: Optional[int] = 2000
    ) -> Dict[str, Any]:
        """Detects the language(s) of the text."""

    @abc.abstractmethod
    def extract_outline(
        self, pdf_path: str
    ) -> List[Any]:  # Use Any for OutlineItem to avoid import complexity now
        """Extracts the document outline (bookmarks/TOC)."""
