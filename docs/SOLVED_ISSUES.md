# Solved Issues for Document Understanding MCP Server

This document tracks issues, limitations, and workarounds that have been resolved in the `document-understanding-mcp-server` project.

## Server Implementation & Core Logic

*   ✅ **Removed Context Management:** The limited and non-robust `context/set_settings` and `context/clear_settings` tools were removed. Tool-specific parameters should be used instead.
*   ✅ **Fixed Type Checking Issues:** Resolved various type errors identified by mypy, including:
    *   Fixed `OCRRunnerCallable` type definition to include the `lang` parameter.
    *   Fixed multiple redefinitions of `self._ocr_runner`.
    *   Fixed `PDFDocument` and `PDFPage` type aliases.
    *   Fixed `needs_pass` check to handle both property and method cases.
    *   Fixed `file_exists_checker` issue by creating a new method `check_file_exists`.
    *   Fixed `ImageDescriptor` constructor.

## Testing & Test Infrastructure

*   ✅ **Dynamic Test PDFs:** Replaced static test PDFs in the repository with dynamically generated PDFs (`tests/pdf_generators.py`) for improved maintainability, portability, and reduced repository size.
*   ✅ **Reliable Integration Testing:** Implemented a new testing approach using the MCP CLI (`tests/integration/test_e2e_mcptools.py`) to overcome reliability issues with previous in-process and stdio tests based on the MCP SDK (hanging fixtures, timeouts).
*   ✅ **Integration Test Setup:**
    *   Added the `create_test_env` fixture to the integration tests.
    *   Created a `conftest.py` file in the integration directory.
*   ✅ **Image Extraction Test Handling:** Updated tests to correctly handle limitations where test PDFs generated with `reportlab.drawImage` do not contain standard raster images detectable by `page.get_images()`. Tests now assert expected behaviour for `extract_images`, `extract_layout`, and `extract_metadata` with such files.
*   ✅ **Test Verification:** Verified that all unit tests, integration tests, and type checking are passing.

## Code Quality & Build

*   ✅ **Unused Import Removal:** Added `autoflake` to project dependencies and `pyproject.toml` configuration, along with a `make fix-imports` target to remove unused imports.
*   ✅ **Linting Fixes:**
    *   Fixed f-strings that were missing placeholders.
    *   Fixed lines exceeding length limits.
    *   Fixed unused variables.
