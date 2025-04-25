# Document Understanding MCP Server

> **⚠️ WARNING**: This server is currently in alpha stage and is intended for local development and testing only. It should not be deployed in production environments or exposed to untrusted networks. Please review [SECURITY.md](SECURITY.md) for important security considerations before running this server.

MCP server providing tools to extract text, metadata, layout, and search documents (primarily PDFs). This server implements the Model Context Protocol (MCP) specification, allowing AI models to interact with PDF documents through a standardized interface.

## Overview

The Document Understanding MCP Server provides a set of tools for extracting information from PDF documents, including:

- Text content extraction (with OCR fallback for scanned documents)
- Metadata extraction (author, title, creation date, etc.)
- Layout information extraction (text blocks, images, drawings)
- Table extraction
- Image extraction
- Document outline/bookmarks extraction
- Text search functionality
- Language detection

These tools can be used by AI models to analyze and understand PDF documents, enabling more sophisticated document processing workflows.

> **Future Plans**: We're working on expanding support to multiple document types beyond PDF. See [docs/plans/README.md](docs/plans/README.md) for details on upcoming architectural changes.

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repo-url>
    cd document-understanding-mcp-server
    ```
2.  **Install Python:** Ensure you have Python **3.11+** installed.
3.  **Install `uv`:** It's recommended to use `uv` for environment management.
    ```bash
    pip install uv
    ```
4.  **Create and Sync Virtual Environment:**
    ```bash
    uv venv # Create .venv
    # Install core dependencies
    uv pip sync pyproject.toml
    # For development/testing, install optional extras:
    uv pip install -e '.[dev,test]'
    ```
5.  **(Required for Table Extraction) Install Java:** The `extract_tables` tool relies on `tabula-py`, which requires a Java Runtime Environment (JRE). Install a JRE (e.g., OpenJDK) suitable for your system and ensure `java` is accessible in your system's PATH.
6.  **(Required for OCR Fallback) Install Tesseract:** The OCR fallback in `extract_pdf_contents` relies on `pytesseract`, which requires the Tesseract OCR engine itself. Install Tesseract for your OS (see [Tesseract Installation](https://tesseract-ocr.github.io/tessdoc/Installation.html)) and ensure the `tesseract` command is in your system's PATH.
7.  **Configure Base Path (Mandatory unless overridden):** Define the `DOCUMENT_UNDERSTANDING_BASE_PATH` environment variable. This is the **only** directory the server will read PDFs from by default. Example:
    ```bash
    export DOCUMENT_UNDERSTANDING_BASE_PATH=/path/to/your/pdf_working_directory
    ```

## Configuration

*   **`DOCUMENT_UNDERSTANDING_BASE_PATH` (Environment Variable, Required*):** Specifies the absolute path to the directory the server is allowed to access for reading PDFs. The server will refuse to start if this is not set, unless `--allow-any-path` is used.
*   **`DOCUMENT_UNDERSTANDING_LOG_LEVEL` (Environment Variable):** Sets the minimum log level for console output (e.g., `DEBUG`, `INFO`, `WARNING`). Default=`INFO`.
*   **`DOCUMENT_UNDERSTANDING_LOG_FORMAT` (Environment Variable):** Sets console log format (`plain` or `json`). Default=`plain`.
*   **`DOCUMENT_UNDERSTANDING_LOG_FILE` (Environment Variable):** If set, specifies a path to write structured JSON logs (e.g., `.tmp/logs/server.log`). Directory will be created. Default=Disabled.
*   **`DOCUMENT_UNDERSTANDING_LOG_FILE_LEVEL` (Environment Variable):** Minimum level for file logging (e.g., `DEBUG`, `INFO`). Default=`INFO`.
*   **`DOCUMENT_UNDERSTANDING_DEFAULT_LANG` (Environment Variable):** Sets the default OCR language (e.g., `eng`, `fra`). Defaults to `eng` if not set.
*   **`ENABLE_SAVE_IMAGES_TO_FILES` (Environment Variable):** When set to `true`, enables saving extracted images to files when using the `extract_images` tool with the `output_directory` parameter. Default=`false`.
*   **`SAFE_OUTPUT_DIRECTORIES` (Environment Variable):** Colon-separated list of directories where images can be saved when `ENABLE_SAVE_IMAGES_TO_FILES=true` but `ALLOW_ANY_PATH=false`. For example: `/tmp:/var/output:/data/images`.
*   **Capability Override / Enable Flags (Command-line):**
    *   `--allow-no-java`: If the Java runtime (required for `extract_tables`) is not found, the server will normally exit. Use this flag to allow startup, but the `extract_tables` tool will be disabled.
    *   `--allow-no-tesseract`: If the Tesseract executable (required for OCR fallback) is not found, the server will normally exit. Use this flag to allow startup, but OCR fallback in `extract_pdf_contents` will be disabled.
    *   `--enable-experimental`: Enables experimental tools (like `find_nearby_content`) which are disabled by default.
    *   `--allow-any-path`: **(SECURITY RISK)** If set, disables the `PDF_SERVER_BASE_PATH` restriction and allows the server to attempt reading files from any path provided in tool arguments. Use with extreme caution and only in trusted environments.

## Capability / Dependency Matrix

The availability or full functionality of certain tools depends on external dependencies or flags.

| Tool Name              | Capability              | Dependency / Trigger | Check Performed At | Control Flag             |
|------------------------|-------------------------|----------------------|--------------------|--------------------------|
| `extract_tables`       | `java_runtime`          | Java Runtime (JRE)   | Server Startup     | `--allow-no-java`        |
| `extract_pdf_contents` | `tesseract_ocr` (Opt.)  | Tesseract OCR        | Server Startup     | `--allow-no-tesseract`   |
| *(Other Tools)*        | *(None)*                | Python Packages      | Installation       | *(N/A)*                  |

*\**Note:* If Tesseract OCR is unavailable (and `--allow-no-tesseract` is used), OCR fallback is disabled.*

## Tools

The server implements the following tools. The list presented to the LLM via the `list_tools` call is dynamic and depends on detected capabilities (e.g., Java availability) and startup flags.
See `src/document_understanding/models.py` for response schemas (e.g., `TextContentResponse`, `MetadataResponse`, etc.). Error responses follow the `ErrorResponse` schema.

*Guidance:* The `pdf_path` argument in all tools must refer to a file path accessible within the server's environment.

### 1. `extract_pdf_contents`
*   **Description**: Extracts text content from specified pages of a local PDF file. Uses direct text extraction with OCR fallback for scanned or image-heavy pages.
*   **Arguments**:
    *   `pdf_path` (string, required): Path to the local PDF file.
    *   `pages` (string, optional): Page spec (1-based, ranges, neg indices). E.g., `"1, 3-5, -1"`. Default=all.
    *   `ocr_language` (string, optional): OCR language(s) for Tesseract (e.g., `"eng"`, `"fra+eng"`). Default='eng'.
    *   `password` (string, optional): Password for encrypted PDFs.
*   **Returns**: `TextContentResponse` JSON.
*   **Guidance**: Best for getting the raw text of pages. Handles OCR automatically if needed. Use `pages` for specific sections. If dealing with non-English scanned text, set `ocr_language`.

### 2. `extract_pdf_metadata`
*   **Description**: Extracts metadata (author, title, dates) and checks for images/drawings in a PDF.
*   **Arguments**:
    *   `pdf_path` (string, required): Path to the local PDF file.
    *   `password` (string, optional): Password for encrypted PDFs.
*   **Returns**: `MetadataResponse` JSON.
*   **Guidance**: Use this first to get an overview of the PDF structure and properties (page count, title, author, etc.) and a hint about whether images/drawings are present.

### 3. `search_pdf_text`
*   **Description**: Searches for exact text occurrences within specified pages and returns bounding boxes.
*   **Arguments**:
    *   `pdf_path` (string, required): Path to the local PDF file.
    *   `query` (string, required): The text to search for (case-sensitive).
    *   `pages` (string, optional): Page spec. Default=all.
    *   `password` (string, optional): Password for encrypted PDFs.
*   **Returns**: `SearchResponse` JSON containing a list of matches with page number and rectangle coordinates.
*   **Guidance**: Useful for finding specific terms or phrases and their location.

### 4. `extract_pdf_layout`
*   **Description**: Extracts detailed layout info: text blocks, drawings, image placements (with coordinates).
*   **Arguments**:
    *   `pdf_path` (string, required): Path to the local PDF file.
    *   `pages` (string, optional): Page spec. Default=all.
    *   `include_images` (boolean, optional): Include image info (xref, bbox, size). Default=False.
    *   `include_drawings` (boolean, optional): Include vector drawing info. Default=False.
    *   `detail_level` (string, optional): Text detail level ('blocks', 'lines', 'words'). Default='blocks'.
    *   `password` (string, optional): Password for encrypted PDFs.
*   **Returns**: `LayoutResponse` JSON containing layout details per page.
*   **Guidance**: Use when spatial relationships are important or to understand page structure. Provides coordinates for text, images, and vector drawings. Can generate large responses for complex pages.

### 5. `extract-images`
*   **Description**: Extracts info about images (raster images, some other objects like Form XObjects).
*   **Arguments**:
    *   `pdf_path` (string, required): Path to the local PDF file.
    *   `pages` (string, optional): Page spec. Default=all.
    *   `include_data` (boolean, optional): If true, include base64 image data. Default=false.
    *   `min_width` (integer, optional): Minimum image width to include in results.
    *   `min_height` (integer, optional): Minimum image height to include in results.
    *   `filter_bbox` (array, optional): Bounding box to filter images by [x0, y0, x1, y1].
    *   `password` (string, optional): Password for encrypted PDFs.
    *   `output_directory` (string, optional): Directory to save extracted images to. Requires `ENABLE_SAVE_IMAGES_TO_FILES=true` environment variable.
    *   `save_without_returning_data` (boolean, optional): If true, save images to files without returning base64 data in response. Default=false.
*   **Returns**: `ImageExtractionResponse` JSON.
*   **Guidance**: Returns image dimensions, page number, and internal reference (`xref`). Bounding box (`bbox`) is optional and may be missing if detection fails (e.g., for Form XObjects). Use `include_data=True` cautiously as it can return very large responses. When `output_directory` is specified and `ENABLE_SAVE_IMAGES_TO_FILES=true`, images will be saved to disk and the response will include file paths. Use `save_without_returning_data=True` to save images to files without including the potentially large base64 data in the response.

### 6. `extract_tables`
*   **Description**: Extracts tables from specified PDF pages into lists of lists.
*   **Arguments**:
    *   `pdf_path` (string, required): Path to the local PDF file.
    *   `pages` (string, optional): `'all'` or comma-separated page numbers (1-based). Default=all.
    *   `password` (string, optional): Password for encrypted PDFs.
*   **Returns**: `TableExtractionResponse` JSON. (Note: Current implementation returns list of dicts, see [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md)).
*   **Guidance**: Best effort table detection using `tabula-py`. Results depend heavily on table formatting (lines, spacing). May be slow. **Note:** This tool requires a Java runtime. If Java is not detected at server startup and the `--allow-no-java` flag was used, this tool will be unavailable.

### 7. `detect-language`
*   **Description**: Detects the language(s) of text content sampled from specified pages (defaults to page 1).
*   **Arguments**:
    *   `pdf_path` (string, required): Path to the local PDF file.
    *   `pages` (string, optional): Page spec for sampling. Default='1'.
    *   `sample_size` (integer, optional): Max characters to sample. Default=2000.
    *   `password` (string, optional): Password for encrypted PDFs.
*   **Returns**: `LanguageDetectionResponse` JSON.
*   **Guidance**: Useful for determining the primary language before processing or translation.

### 8. `extract_pdf_outline`
*   **Description**: Extracts the document outline (bookmarks/table of contents) from a PDF.
*   **Arguments**:
    *   `pdf_path` (string, required): Path to the local PDF file.
    *   `password` (string, optional): Password for encrypted PDFs.
*   **Returns**: `OutlineExtractionResponse` JSON containing the hierarchical outline structure.
*   **Guidance**: Use to extract the document's table of contents or bookmark structure. Returns an empty list if the document has no outline.

### 9. `get_pdf_working_directory`
*   **Description**: Returns the designated directory path where PDF files should be placed for processing.
*   **Arguments**: None.
*   **Returns**: JSON with `status`, `working_directory` (string or null), and optional `message`.
*   **Guidance**: Call this tool to find out where to upload/place PDF files before calling other tools that require a `pdf_path`. If the server was started with `--allow-any-path`, `working_directory` will be null.

## Testing

The test suite uses dynamically generated PDFs for all tests. No static PDF files are stored in the repository. The test fixtures in `tests/conftest.py` generate all necessary test PDFs at runtime, including:

- Simple text documents
- Documents with images
- Documents with drawings
- Documents with tables
- Documents with outlines/bookmarks
- Empty documents
- Encrypted documents

This approach ensures that all tests can run without requiring external files and makes the test suite more portable and self-contained.

### Running Tests

```bash
# Run all tests
python -m pytest

# Run specific test categories
python -m pytest tests/unit
python -m pytest tests/integration

# Run tests with coverage
python -m pytest --cov=src
```

### Test Architecture

The test suite includes several types of tests:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test the interaction between components
- **End-to-End Tests**: Test the entire system from the user's perspective

The end-to-end tests use the MCP command-line interface to interact with the server, simulating real-world usage. This approach ensures that the server works correctly in various scenarios and with different types of PDFs.

## Running the Server / Invocation

This server runs using the standard MCP stdio communication. There are multiple ways to run the server:

### Method 1: Using the Provided Executable (Recommended)

```bash
# Set required base path (if not using sandbox mode)
export DOCUMENT_UNDERSTANDING_BASE_PATH=/path/to/pdf/storage

# Run with default settings (sandbox mode)
bin/document-understanding-mcp-server

# Run with sandbox mode disabled (less restricted)
DOCUMENT_UNDERSTANDING_SANDBOX=false bin/document-understanding-mcp-server

# Run with additional arguments
bin/document-understanding-mcp-server --enable-experimental --port 8000
```

The `document-understanding-mcp-server` executable automatically sets up a secure environment with:
- User-specific isolated directories in sandbox mode (default)
- Appropriate permissions based on security context
- Intelligent argument handling based on environment

### Method 2: Using Installed Package Entry Point

When the package is installed via pip, you can use the entry point directly:

```bash
# Run with default settings
document-understanding-mcp-server

# Run with custom arguments
document-understanding-mcp-server --allow-any-path --enable-experimental
```

### Method 3: Using `standalone_server.py` Directly

```bash
# Activate environment
source .venv/bin/activate

# Set required base path
export DOCUMENT_UNDERSTANDING_BASE_PATH=/path/to/pdf/storage

# Run directly (will fail if Java/Tesseract missing and flags not used)
python standalone_server.py

# Run allowing missing Java/Tesseract but restricting path
python standalone_server.py --allow-no-java --allow-no-tesseract

# Run allowing ANY path access (UNSAFE)
# DOCUMENT_UNDERSTANDING_BASE_PATH is ignored here
python standalone_server.py --allow-any-path

# Enable experimental features
python standalone_server.py --enable-experimental
```

### Sandbox Mode

The server supports a secure sandbox mode (enabled by default) that:

1. Creates isolated user-specific directories for file output
2. Sets stricter file permissions (700 - user access only)
3. Disables the `--allow-any-path` flag for better security

To disable sandbox mode (not recommended for production):

```bash
export DOCUMENT_UNDERSTANDING_SANDBOX=false
```

### Invocation Command (Example `mcp.json`)

#### Example 1: Basic Configuration

```json
{
  "mcpServers": {
    "document-understanding": {
      "command": "/path/to/document-understanding-mcp-server",
      "args": [
        "--enable-experimental"
      ]
    }
  }
}
```

#### Example 2: Using Python Module Directly

```json
{
  "mcpServers": {
    "document-understanding": {
      "command": "/path/to/your/.venv/bin/python",
      "args": [
        "-m", "document_understanding.cli"
      ],
      "env": {
        "DOCUMENT_UNDERSTANDING_BASE_PATH": "/path/to/pdf/storage"
      }
    }
  }
}
```

## LLM Usage Advice

*   **File Paths:** Before processing a PDF, use `get_pdf_working_directory` to find the allowed directory. Ensure any `pdf_path` arguments you provide refer to files within that directory (or subdirectories). Path traversal attempts (`../`) or absolute paths outside the working directory will be rejected unless the server was unsafely started with `--allow-any-path`.
*   **Passwords:** Currently, the server **cannot** handle password-protected PDFs for most tools (except table extraction). Processing encrypted files will likely fail. See [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md).
*   **Tool Availability:** The list of available tools might change depending on the server's environment (e.g., if Java is missing and `--allow-no-java` was used, `extract_tables` will not be listed). Rely on the response from `list_tools` to know what is currently usable.
*   **Use specific tools:** Prefer `search_pdf_text` over extracting all content if you only need specific occurrences. Use `extract_pdf_metadata` if only metadata is needed.
*   **Handle JSON:** Expect JSON responses. Parse the `text` field of the `ToolResponseContent` as JSON.
*   **Check `status`:** Always check the `status` field in the JSON response. If it's `"error"`, use the `message` and `error_code` fields for diagnostics (Note: errors are typically raised as exceptions by the server, the MCP client translates these).
*   **Layout Information:** The `extract_pdf_layout` tool provides rich structural information (text coordinates, drawings, image locations). This can be used for complex analysis (e.g., with `find_nearby_content`) but generates large responses.
*   **Page Specification:** Use the `pages` parameter effectively (e.g., "1-3, 5, -1") to limit processing when needed.
*   **OCR Language:** If processing non-English documents, specify the language(s) using `ocr_language` (e.g., `"fra+eng"` for French and English) for better accuracy.
*   **Error Handling:** Be prepared for `FileNotFoundError` if the `pdf_path` is incorrect, or `ValueError` for invalid page specifications or processing issues. Encrypted files may cause various errors. The server raises exceptions which the MCP client should surface.

## Complex Usage Examples

1.  **Extracting French Text from Scanned Pages 2 & 3:**
    *   `get_pdf_working_directory` -> Check response for `working_directory`.
    *   *(LLM/User ensures `mydoc.pdf` is in the working directory)*
    *   `extract_pdf_contents` with `pdf_path="mydoc.pdf"`, `pages="2-3"`, `ocr_language="fra"`.
    *   Parse response, process text from the `pages` list.

2.  **Finding Text near an Image:**
    *   `get_pdf_working_directory` -> Get `working_directory`.
    *   *(LLM/User places `report.pdf`)*
    *   `extract_pdf_layout` with `pdf_path="report.pdf"`, `pages="5"` (assuming image is on page 5).
    *   Parse layout response. Identify the desired image based on `xref`, size, or rough `bbox`.
    *   `find_nearby_content` (if enabled) with `pdf_path="report.pdf"`, `pages="5"`, `target_bbox` set to the image's bbox, `content_type="text_block"`, `direction="below"` (e.g., to find caption).
    *   Parse nearby response for the caption text.

3.  **Extracting Specific Tables after Metadata Check:**
    *   `get_pdf_working_directory` -> Get `working_directory`.
    *   *(LLM/User places `data.pdf`)*
    *   `extract_pdf_metadata` with `pdf_path="data.pdf"`.
    *   Check response: confirm `page_count`, look at metadata fields.
    *   `extract_tables` with `pdf_path="data.pdf"`, `pages="2, 4"` (e.g., only pages 2 and 4).
    *   Parse response.

## Critical Use Pathways

1.  **Extract Specific Pages:**
    *   Call `extract_pdf_contents` with `pdf_path` and `pages="2-3"`.
    *   Parse JSON response, check `status`, process the extracted content.

## Known Issues and Limitations

For a list of current known issues and limitations, see [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md).

For a list of previously resolved issues, see [docs/SOLVED_ISSUES.md](docs/SOLVED_ISSUES.md).

## Future Plans

For information about planned enhancements and future development, see the [plans directory](docs/plans/README.md).

## Contributing

For information on how to contribute to this project, please see the [CONTRIBUTING.md](CONTRIBUTING.md) file.

## License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.