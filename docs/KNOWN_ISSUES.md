# Known Issues for Document Understanding MCP Server

This document tracks known issues, limitations, and workarounds in the `document-understanding-mcp-server` project and its dependencies.

## Server Implementation Issues

### 1. PyMuPDF Segfault with `-W error`

*   **Issue:** Running `pytest` with the `-W error` flag (to treat warnings as errors) causes a segmentation fault during the import of `fitz` (from `pymupdf==1.25.5` on Python 3.13).
*   **Cause:** Seems related to `DeprecationWarning`s originating from `pymupdf`'s SWIG C bindings interacting poorly with Python's strict warning handling.
*   **Investigation:**
    *   Confirmed the segfault occurs even in a minimal virtual environment with only `pymupdf` installed when `-W error` is used.
    *   Attempting to build `pymupdf` from source (`--no-binary pymupdf`) failed due to C header conflicts (specifically `fdopen` macro in bundled `zlib` vs system headers on macOS).
    *   Updating `pymupdf` via pip did not yield a newer version at the time of testing.
*   **Workaround:** The global `-W error` flag cannot be reliably used for the test suite. We have removed it from `pytest`'s `addopts` in `pyproject.toml`. Specific `DeprecationWarning`s from `pymupdf.*` and `<sys>` related to SWIG types are explicitly ignored using `filterwarnings` in `pyproject.toml` to keep the standard test output clean.
*   **Future:** Monitor future `pymupdf` releases or investigate further if running with `-W error` becomes critical.

### 2. Image Extraction Limitations

*   **Issue:** The `extract_images` tool has limitations when detecting certain types of images in PDF files.
*   **Details:** Some image types, particularly those embedded as Form XObjects, may not be detected by `page.get_images()` used in the `extract_images` tool.
*   **Impact:** Users may not get all expected images when using the `extract_images` tool on PDFs with certain types of embedded images.
*   **Future:** Enhance the image extraction functionality to detect and extract a wider range of image types from PDF files.

### 3. Table Extraction Dependencies

*   **Issue:** The `extract-tables` tool relies on `tabula-py`.
*   **Requirement:** `tabula-py` requires a **Java runtime environment** to be installed and accessible in the system's PATH.
*   **Testing:** Tests involving `extract_tables` might fail with a `RuntimeError` if Java is not found. The `test_extract_tables_no_tables` test currently attempts to detect this but will fail the test run if Java is missing.

### 4. Spurious `pytest-timeout` Configuration Warning

*   **Issue:** Running `pytest` shows `PytestConfigWarning: Unknown config option: timeout` despite `timeout = 0.5` being the documented correct configuration under `[tool.pytest.ini_options]` in `pyproject.toml`.
*   **Cause:** Likely a spurious warning due to pytest/plugin version interactions or `pyproject.toml` parsing in the specific environment.
*   **Workaround:** The warning is explicitly ignored using `filterwarnings` in `pyproject.toml` to keep test output clean. The timeout functionality appears to work correctly regardless.

### 6. Missing Password Parameter/Handling for Most Tools

*   **Issue:** Most extraction tools (content, layout, metadata, outline, etc.) rely on PyMuPDF which needs a password provided *at file open time* to handle encrypted PDFs. However, some tool definitions in `server.py` might not include a `password` parameter, or the internal helpers might not properly handle passwords.
*   **Impact:** Tools might fail on password-protected PDFs, often with generic errors, instead of a specific `PDFPasswordError`. Users might have difficulty processing these common files.
*   **Exception:** Table extraction *does* now raise `PDFPasswordError` because the underlying `tabula-java` process returns a specific error message that is now caught.
*   **Future:** Ensure all tools have an optional `password: str` parameter in their input schema in `server.py`. Verify that all internal helpers properly accept and use this password when calling `fitz.open()`. Ensure consistent `PDFPasswordError` raising across all tools.

### 7. Inconsistent Table Extraction Return Type

*   **Issue:** The `extract_tables` method (and its implementation `_extract_tables_impl`) currently returns a `List[dict]`, where each dictionary represents a table.
*   **Mismatch:** The expected return type based on `models.py` (which defines a `Table` Pydantic model) and the likely intended schema in `server.py` is `List[Table]` (or wrapped in a `TableExtractionResponse`).
*   **Impact:** Clients might encounter deserialization errors or type inconsistencies if they expect typed `Table` objects based on the server's advertised schema.
*   **Future:** Refactor `_extract_tables_impl` or `extract_tables` to construct and return instances of the `Table` model from `models.py` instead of raw dictionaries.

### 8. Missing `extract_content` Enhancements

*   **Status:** A previously skipped test indicated planned enhancements for the `extract_content` tool, specifically adding `detail_level` (similar to `extract_layout`) and `default filtering` options.
*   **Limitation:** These features are not currently implemented.
*   **Future:** Consider implementing these features if desired to enhance content extraction capabilities. Requires defining the exact behaviour and updating the implementation and tool schema.

### 9. Untested Standalone Server (`standalone_server.py`)

*   **Issue:** The `standalone_server.py` script, responsible for the command-line interface, argument parsing (including `--base-path`, `--allow-any-path`, capability flags), and initializing server capabilities, currently has limited unit test coverage.
*   **Impact:** Potential bugs in CLI argument handling, path validation logic, or capability detection (like checking for Java) may not be fully covered by automated tests.
*   **Future:** Enhance unit tests for `standalone_server.py` and `standalone_config.py` to cover argument parsing, configuration loading, capability detection logic, and path validation rules.

## MCP SDK Issues

### 10. Stdio Transport Framing Inconsistency / Hang

*   **Versions Affected:** Tested on `1.4.1` and `1.6.0`.
*   **Context:** When running an MCP server using `mcp.server.stdio.stdio_server` as a subprocess managed by `asyncio.create_subprocess_exec`.
*   **Symptoms:**
    *   If the test client sends messages using standard JSON-RPC Content-Length framing, the server appears to hang before processing the first (`initialize`) request, leading to client timeouts.
    *   If the test client sends messages using newline-delimited JSON (matching the SDK's `stdio.py` implementation), the `initialize` handshake succeeds, but subsequent requests (e.g., `tools/list`) often lead to timeouts.
*   **Suspected Cause:** The `mcp.server.stdio.stdio_server` implementation (specifically `stdin_reader` in `stdio.py`) reads from stdin line-by-line (`async for line in stdin:`). This seems inconsistent with the MCP specification's requirement that messages MUST NOT contain embedded newlines and contradicts standard Content-Length based framing used in similar protocols like LSP. While the spec *also* mentions messages are newline-delimited, the SDK's line-by-line reading appears fragile and unable to reliably parse incoming requests in an `asyncio` subprocess stdio environment.
*   **Impact:** Makes reliable E2E testing via stdio subprocesses extremely difficult or impossible with the current SDK implementation.
*   **Status:** Test `tests/integration/test_e2e_stdio.py` is marked `xfail`.