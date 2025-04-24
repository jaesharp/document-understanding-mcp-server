"""Custom exceptions for the PDF extraction process."""


class PDFExtractionError(Exception):
    """Base exception for PDF extraction failures."""


class PDFPasswordError(PDFExtractionError):
    """Exception raised when a PDF is password-protected and cannot be opened."""


class OCRUnusableError(PDFExtractionError):
    """Exception raised when OCR is needed but cannot be performed."""


class TableExtractionError(PDFExtractionError):
    """Exception raised during table extraction (e.g., Java issues)."""


class LanguageDetectionError(PDFExtractionError):
    """Exception raised during language detection."""
