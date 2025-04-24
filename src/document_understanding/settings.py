# src/document_understanding/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional, Literal


class Settings(BaseSettings):
    """Server static configuration settings (from environment variables)."""

    # Load ONLY from environment variables, case_sensitive allows lowercase env vars
    model_config = SettingsConfigDict(
        env_prefix="DOCUMENT_UNDERSTANDING_",  # Prefix for environment variables
        case_sensitive=False,
    )

    # Logging configuration
    log_level: str = Field(
        default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    log_format: Literal["plain", "json"] = Field(
        default="plain", description="Logging format ('json' or 'plain')"
    )

    # Potentially dynamic settings moved out - will be handled by context or defaults
    default_ocr_language: str = Field(
        default="eng",
        alias="PDF_EXTRACTOR_DEFAULT_LANG",
        description="Default Tesseract language(s)",
    )
    min_text_length_for_non_ocr: int = Field(
        default=50, description="Min chars on page to skip OCR"
    )

    # File Logging Configuration
    log_file: Optional[str] = Field(
        default=None,
        description="Path to write structured JSON logs. Disabled if not set.",
    )
    log_file_level: str = Field(
        default="INFO", description="Minimum log level for the file logger."
    )


# Instantiate settings globally for easy import
settings = Settings()
