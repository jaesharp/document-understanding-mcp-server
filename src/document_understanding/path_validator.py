"""
Path validation utilities for document understanding server.

This module handles all path validation and resolution functions.
"""

import os
from typing import Optional, Any, Tuple

from .logging_config import get_logger

logger = get_logger(__name__)


class PathValidator:
    """
    Validates and resolves file paths based on server configuration.
    """

    def __init__(self, base_path: Optional[str], allow_any_path: bool):
        """
        Initialize the path validator with server configuration.

        Args:
            base_path: Base directory for relative paths or None
            allow_any_path: Whether to allow arbitrary paths
        """
        self.base_path = base_path
        self.allow_any_path = allow_any_path

    def validate_and_resolve_path(self, untrusted_path: str) -> str:
        """
        Resolves path relative to base_path and ensures it's within bounds.

        Args:
            untrusted_path: The path to validate and resolve

        Returns:
            The validated absolute path

        Raises:
            ValueError: If the path is invalid or outside allowed directories
            RuntimeError: If server configuration is invalid
        """
        logger.debug(
            "Validating path",
            untrusted_path=untrusted_path,
            base_path=self.base_path,
            allow_any=self.allow_any_path,
        )

        if self.allow_any_path:
            abs_path = os.path.abspath(untrusted_path)
            logger.debug("Allowing any path, resolved to", abs_path=abs_path)
            return abs_path

        if not self.base_path:
            raise RuntimeError(
                "Server configuration error: Base path not set despite restriction being enabled."
            )

        try:
            abs_path = os.path.abspath(os.path.join(self.base_path, untrusted_path))

            # Security Check: Ensure the resolved path is still within the BASE_PATH
            normalized_base_path = os.path.normpath(self.base_path)
            if (
                os.path.commonpath([normalized_base_path, abs_path])
                != normalized_base_path
            ):
                raise ValueError(
                    f"Path is outside the allowed base directory: {untrusted_path}"
                )

            return abs_path
        except Exception as e:
            raise ValueError(
                f"Invalid or problematic path provided: {untrusted_path} - {e}"
            )

    def is_valid_string_path(self, path_value: Any) -> bool:
        """
        Check if the provided value is a valid non-empty string path.

        Args:
            path_value: The value to check

        Returns:
            True if the value is a valid string path, False otherwise
        """
        return isinstance(path_value, str) and bool(path_value)

    def validate_and_prepare_args(
        self, name: str, arguments: dict
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Validates common arguments like pdf_path, resolves path, and returns validated path and pages string.

        Args:
            name: The tool name
            arguments: The tool arguments

        Returns:
            A tuple containing the validated pdf_path (or None) and pages_str (or None)

        Raises:
            ValueError: If required arguments are missing or invalid, or path validation fails
        """
        pdf_path_untrusted = arguments.get("pdf_path")
        pages_str = arguments.get("pages")  # Optional argument

        pdf_required_tools = {
            "extract_pdf_contents",
            "extract_pdf_layout",
            "extract_pdf_metadata",
            "search_pdf_text",
            "extract_images",
            "extract_tables",
            "detect_language",
            "extract_pdf_outline",
        }

        is_pdf_required = name in pdf_required_tools
        validated_pdf_path = None

        if is_pdf_required:
            self._validate_required_pdf_path(name, pdf_path_untrusted)
            validated_pdf_path = self._resolve_validated_path(
                name, pdf_path_untrusted, True
            )
        elif pdf_path_untrusted:
            self._validate_optional_pdf_path(pdf_path_untrusted)
            validated_pdf_path = self._resolve_validated_path(
                name, pdf_path_untrusted, False
            )

        return validated_pdf_path, pages_str

    def _validate_required_pdf_path(
        self, tool_name: str, pdf_path_untrusted: Any
    ) -> None:
        """
        Validate that a required PDF path is provided and is a valid string.

        Args:
            tool_name: The name of the tool
            pdf_path_untrusted: The path to validate

        Raises:
            ValueError: If the path is missing, empty, or not a string
        """
        if pdf_path_untrusted is None:
            raise ValueError(f"pdf_path is required for {tool_name}")

        if not self.is_valid_string_path(pdf_path_untrusted):
            raise ValueError("Missing or invalid required argument: pdf_path")

    def _validate_optional_pdf_path(self, pdf_path_untrusted: Any) -> None:
        """
        Validate an optional PDF path if provided.

        Args:
            pdf_path_untrusted: The path to validate

        Raises:
            ValueError: If the path is provided but is empty or not a string
        """
        if pdf_path_untrusted is not None and not self.is_valid_string_path(
            pdf_path_untrusted
        ):
            raise ValueError("Invalid optional argument: pdf_path")

    def _resolve_validated_path(
        self, tool_name: str, pdf_path_untrusted: Optional[str], is_required: bool
    ) -> str:
        """
        Resolve and validate a path using the path validation logic.

        Args:
            tool_name: The name of the tool
            pdf_path_untrusted: The path to validate
            is_required: Whether the path is required

        Returns:
            The validated and resolved path

        Raises:
            ValueError: If path validation fails
        """
        context = "required" if is_required else "optional"

        if pdf_path_untrusted is None:
            if is_required:
                logger.warning(f"Missing required pdf_path for tool {tool_name}")
                raise ValueError("Missing required argument: pdf_path")
            return ""  # Return empty string for optional paths

        try:
            validated_path = self.validate_and_resolve_path(pdf_path_untrusted)
            logger.debug(
                "Validated {} pdf_path for {}: {}".format(
                    context, tool_name, validated_path
                )
            )
            return validated_path
        except (ValueError, FileNotFoundError) as path_err:
            logger.warning(
                f"Invalid or inaccessible {context} pdf_path for tool {tool_name}: {path_err}",
                provided_path=pdf_path_untrusted,
            )
            raise ValueError(
                f"Invalid or inaccessible pdf_path: {path_err}"
            ) from path_err
