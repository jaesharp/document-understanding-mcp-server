# Contributing to the Document Understanding MCP Server

Thank you for considering contributing! Please adhere to the following guidelines.

> **Note**: The Document Understanding MCP Server is planning significant architectural changes to support multiple document types beyond PDF. See [docs/plans/README.md](docs/plans/README.md) for details on upcoming changes.

## Testing Guidelines

When writing tests for the Document Understanding MCP Server, please follow the mocking and stubbing patterns described in [docs/MOCKING_AND_STUBBING.md](docs/MOCKING_AND_STUBBING.md). This document provides detailed examples of how to mock PyMuPDF objects, file system operations, and external dependencies like Java and Tesseract.

### Dynamic PDF Generation for Testing

All tests should use dynamically generated PDFs instead of static PDF files. The project has completed a transition from static to dynamic test PDFs as described in [docs/plans/pdf_testing_transition_plan.md](docs/plans/pdf_testing_transition_plan.md). When writing new tests, use the PDF generation functions and fixtures provided in `tests/conftest.py`.

## Code Quality and Security

### Linting and Type Checking

The project uses several tools to ensure code quality:
- **Black** for code formatting
- **Flake8** for linting
- **MyPy** for type checking

You can run these checks locally using the following commands:
```bash
make format      # Format code with Black
make lint        # Run Flake8 linting
make typecheck   # Run MyPy type checking
```

### Security Scanning

We use Bandit to perform static security analysis of the codebase. Bandit helps identify common security issues in Python code, such as use of `assert` statements (which are removed when running with optimisations), unsafe use of `eval()`, and other potential vulnerabilities.

To run the security check locally:
```bash
make security-check
```

This scan is also part of our CI pipeline, ensuring that security standards are maintained across all contributions. When making changes, especially to code that handles user input or file system operations, ensure that the security check passes.

Common security issues to avoid:
- Using `assert` for validation (use proper validation with if/raise instead)
- Using `eval()` or `exec()` on untrusted input
- Path traversal vulnerabilities
- Hard-coded credentials or sensitive information

## Documentation Strategy

Maintaining clear documentation for both human developers and the LLM agent using the server is crucial. We use a multi-layered approach:

1.  **`README.md` (Primary Human Source):**
    *   **Target Audience:** Developers setting up, running, or contributing to the server.
    *   **Content:** Must include comprehensive setup instructions (including *all* external dependencies like Java), configuration details (env vars, command-line flags), a tool overview (arguments, returns), LLM usage advice, server invocation examples, and known issues/limitations.
    *   **Maintenance:** Keep up-to-date with any changes in dependencies, configuration, or tool functionality.

2.  **`handle_list_tools` Function (Primary LLM Source):**
    *   **Target Audience:** LLM agent.
    *   **Content:** This function in `src/document_understanding/server.py` dynamically generates the list of tools available to the LLM. Descriptions should be concise, LLM-focused, and provide operational guidance. **Crucially, tools that cannot run due to missing dependencies (and an override flag being set) MUST be omitted from this list.** Tool schemas (`inputSchema`, `outputSchema`) should accurately reflect the expected inputs and outputs.
    *   **Maintenance:** Update schemas and descriptions whenever tool signatures or behaviour changes. Ensure conditional logic for tool availability based on dependencies is correctly implemented.

3.  **Code Docstrings:**
    *   **Target Audience:** Developers.
    *   **Content:** Standard Python docstrings for modules, classes, and functions explaining their purpose, arguments, and return values.
    *   **Maintenance:** Keep docstrings synchronised with code logic.

## Capability-Based Dependency Handling

To manage external dependencies or optional features gracefully, we use a capability-based system. This allows the server to start even if some dependencies are missing, disabling only the tools that strictly require them, and potentially degrading the functionality of others (like OCR fallback).

1.  **Define Capabilities & Requirements:**
    *   Identify capabilities linked to external dependencies (e.g., `java_runtime` for `tabula-py`, `tesseract_ocr` for `pytesseract`).
    *   Define check functions for each capability (e.g., `check_java_runtime()`, `check_tesseract()`).
    *   In `src/document_understanding/server.py`, maintain a dictionary `TOOL_CAPABILITIES_REQUIRED` mapping tool names to a list of capability strings they *strictly* need to function at all (e.g., `{"extract_tables": ["java_runtime"]}`). Tools with *optional* dependencies (like OCR fallback) are not listed here but handle the capability check internally.

2.  **Startup Checks & Overrides:**
    *   In `standalone_server.py`:
        *   Maintain a central `CAPABILITIES` dictionary mapping capability names to their check function, override flag (`--allow-no-<capability>`), help text, and error message.
        *   Use `argparse` to automatically create override flags based on the `CAPABILITIES` dictionary.
        *   At startup, run all capability checks.
        *   Store the results (True/False) in a `capability_status` dictionary (e.g., `{"java_runtime": True, "tesseract_ocr": False}`).
        *   For each capability check that fails:
            *   If the corresponding override flag is *not* set, print an error and exit.
            *   If the flag *is* set, print a warning.
        *   Pass the final `capability_status` dictionary to the `src/document_understanding/server.py` module (e.g., `server.SERVER_CAPABILITIES = capability_status`).

3.  **Dynamic Tool Listing (`handle_list_tools`):**
    *   In `src/document_understanding/server.py`, `handle_list_tools` accesses `server.SERVER_CAPABILITIES`.
    *   It filters the list of all potential tools based on `TOOL_CAPABILITIES_REQUIRED`. Only tools whose strictly required capabilities are `True` are included.
    *   For tools with *optional* capabilities (like `extract_pdf_contents` and OCR), the tool description may be dynamically updated to indicate if the optional feature is currently enabled/disabled based on `SERVER_CAPABILITIES`.

4.  **Runtime Capability Handling:**
    *   **Strict Requirements (`handle_call_tool`):** For tools listed in `TOOL_CAPABILITIES_REQUIRED`, add a runtime check at the beginning of their execution block in `handle_call_tool` that verifies the required capabilities from `SERVER_CAPABILITIES`. Raise a `RuntimeError` if a check fails (safeguard).
    *   **Optional Capabilities (`PDFExtractor`):** For tools with optional features depending on capabilities (like OCR), the capability status dictionary (`SERVER_CAPABILITIES`) should be passed to the relevant class (e.g., `PDFExtractor` during instantiation). The class methods then check the status internally before attempting to use the capability (e.g., `_extract_page_text` checks `self.capabilities.get('tesseract_ocr')` before trying OCR).

This ensures:
*   Clear feedback on missing dependencies during setup.
*   Optional startup with degraded functionality.
*   The LLM sees an accurate list of available tools and potentially notes about disabled optional features within tool descriptions.

## Critical Test Pathways

When making changes, especially to core extraction logic or the server API, ensure the following critical pathways are tested thoroughly, primarily via the in-process E2E tests (`tests/integration/test_e2e_in_process.py`):

1.  **Server Initialization:** Verify the server starts, reports correct capabilities (considering enabled features like experimental), and responds to `initialize` correctly.
2.  **Tool Listing:** Ensure `tools/list` returns the expected set of tools based on server capabilities (e.g., experimental tools should only appear if enabled).
3.  **Basic Tool Invocation (`extract_pdf_metadata`):** Test a simple tool that reads metadata from a known PDF.
4.  **Content Extraction (`extract_pdf_contents`):**
    *   Test extraction from a simple text-based PDF.
    *   Test extraction requiring OCR fallback (if Tesseract is enabled/mocked).
    *   Test with page range selections.
    *   Test handling of OCR language settings (via `context/set_settings`).
5.  **Layout Extraction (`extract_pdf_layout`):** Test extraction of layout elements (text blocks, images, drawings) from a PDF with mixed content.
6.  **Search (`search_pdf_text`):** Test searching for known text and verify bounding box results.
7.  **Image Extraction (`extract_images`):** Test identification of images, potentially including data extraction if feasible in tests.
8.  **Table Extraction (`extract_tables`):** Test table extraction from a PDF with well-defined tables (requires Java or mocking).
9.  **Experimental Features (`find_nearby_content`, others):** If enabled, test specific experimental tools with appropriate inputs.
10. **Context Management (`context/set_settings`, `context/clear_settings`):** Verify that setting context affects subsequent tool calls (e.g., OCR language) and that clearing resets behavior.
11. **Path Handling:**
    *   Verify `get_pdf_working_directory` returns the correct path when restrictions are enabled.
    *   Verify tools correctly resolve relative paths within the `BASE_PATH`.
    *   Verify tools reject paths attempting to escape the `BASE_PATH` (when restrictions are enabled).
    *   Verify behavior when `ALLOW_ANY_PATH` is enabled (if applicable to test scenarios).
12. **Error Handling:** Test invalid tool calls (bad arguments, missing files) and verify appropriate JSON-RPC error responses are returned.

These pathways cover the core functionality. Add specific tests for new features or complex interactions as needed.