"""
Type stubs for PyMuPDF (fitz) to help mypy understand the types.
This is not a complete stub file, but it contains the types needed for our code.
"""

from typing import Any, Dict, List


class PDFPage:
    """Stub for fitz.Page class."""

    number: int

    def get_text(self, mode: str, flags: int = 0, sort: bool = False) -> str:
        """Get text from page."""
        return ""

    def get_pixmap(self, dpi: int = 72) -> Any:
        """Get pixmap from page."""
        return None

    def search_for(self, text: str, **kwargs) -> List[Any]:
        """Search for text on page."""
        return []

    def get_images(self, full: bool = False) -> List[Any]:
        """Get images from page."""
        return []

    def get_drawings(self, **kwargs) -> List[Any]:
        """Get drawings from page."""
        return []

    def get_image_rects(self, img_list: List[Any], transform: bool = True) -> List[Any]:
        """Get image rectangles from page."""
        return []


class PDFDocument:
    """Stub for fitz.Document class."""

    page_count: int
    metadata: Dict[str, str]

    def __enter__(self) -> "PDFDocument":
        """Context manager enter."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        return None

    def load_page(self, page_number: int) -> PDFPage:
        """Load a page."""
        return PDFPage()

    def close(self) -> None:
        """Close the document."""
        return None

    def needs_pass(self) -> bool:
        """Check if document needs a password."""
        return False

    def authenticate(self, password: str) -> bool:
        """Authenticate with password."""
        return True

    def get_toc(self) -> List[List[Any]]:
        """Get table of contents."""
        return []

    def extract_image(self, xref: int) -> Dict[str, Any]:
        """Extract image by xref."""
        return {}
