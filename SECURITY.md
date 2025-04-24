# Security Considerations for Document Understanding MCP Server

## Current Security Measures

### File System Access (`DOCUMENT_UNDERSTANDING_BASE_PATH` and `--allow-any-path`)

*   **Risk:** The server processes local PDF files specified by path. Allowing arbitrary file path access from the LLM or client introduces a significant security risk. An attacker could potentially request paths pointing to sensitive system files (e.g., `/etc/passwd`, configuration files, credentials) or cause denial-of-service by requesting large or numerous files.
*   **Mitigation:**
    *   By default, the server **requires** the `DOCUMENT_UNDERSTANDING_BASE_PATH` environment variable to be set during startup. This variable defines the *only* directory (and its subdirectories) from which the server will accept `pdf_path` arguments.
    *   The server performs path validation on every incoming `pdf_path` to ensure it resolves to a location *within* the configured `DOCUMENT_UNDERSTANDING_BASE_PATH`. Path traversal attempts (`../`) or absolute paths outside this base directory will be rejected with an error.
    *   The `--allow-any-path` command-line flag completely disables this restriction. **This flag should ONLY be used in highly controlled, trusted environments where the operator fully understands and accepts the risks.** It is strongly discouraged for production or multi-user scenarios.
*   **LLM Guidance:** The LLM should use the `get_pdf_working_directory` tool to discover the allowed base path before attempting to process files.

### External Dependencies (Java Runtime, Tesseract OCR)

*   **Risk:** The server relies on external executables (`java` for `extract-tables`, `tesseract` for OCR fallback). If these executables are compromised or vulnerable versions are installed, they could potentially be exploited when called by the server.
*   **Mitigation:**
    *   Ensure that Java and Tesseract are installed from trusted sources and kept up-to-date with security patches.
    *   Run the server in a sandboxed or containerised environment with minimal privileges to limit the potential impact of a compromised dependency.
    *   If a dependency is not needed (e.g., table extraction is never used), consider *not* installing it and using the corresponding `--allow-no-...` flag (e.g., `--allow-no-java`) during server startup. This disables the related tool and avoids calling the external executable entirely.

### Resource Consumption (Large Files, Complex PDFs, OCR)

*   **Risk:** Processing very large or complex PDF files, or performing OCR on many pages, can consume significant CPU, memory, and time, potentially leading to denial-of-service (DoS) for other requests or the server host.
*   **Mitigation:**
    *   Run the server with appropriate resource limits (CPU, memory) using mechanisms like `cgroups`, container limits, or process management tools.
    *   Implement timeouts for tool calls (the example `mcp.json` shows `toolCallTimeoutMillis`).
    *   Consider adding input validation or limits on the number of pages processed in a single request, although this is not currently implemented.

### Input Handling (Malformed PDFs, Tool Arguments)

*   **Risk:** Specially crafted, malformed PDF files could potentially exploit vulnerabilities in the underlying `PyMuPDF` library. Invalid tool arguments could cause unexpected errors.
*   **Mitigation:**
    *   Keep the `PyMuPDF` library and other Python dependencies up-to-date.
    *   The server includes basic argument validation (e.g., checking for required arguments like `pdf_path`) and extensive `try...except` blocks to catch errors during processing, preventing uncaught exceptions from crashing the server.
    *   Input schemas defined in `handle_list_tools` help the LLM provide valid arguments.

## Outstanding Security Evaluations

### Input Validation

*   **Status:** Needs comprehensive review
*   **Areas to Check:**
    *   File path handling in `server.py` and `standalone_server.py`
    *   Parameter validation in all tool handlers
    *   JSON parsing and serialization
*   **Required Actions:**
    *   Review all user input points for proper validation
    *   Verify that path traversal attacks are properly prevented in all cases
    *   Ensure all parameters are properly validated before use
    *   Add validation for any missing parameters
    *   Implement consistent error handling for invalid inputs

### File Access

*   **Status:** Needs comprehensive review
*   **Areas to Check:**
    *   File path handling in `server.py` and `extractor/` modules
    *   Base path enforcement implementation
    *   Temporary file handling (if any)
*   **Required Actions:**
    *   Review all file access points for proper path validation
    *   Verify that base path restrictions are consistently enforced
    *   Ensure any temporary files are properly cleaned up
    *   Add proper cleanup for any temporary files that might be created

### Error Handling

*   **Status:** Needs comprehensive review
*   **Areas to Check:**
    *   Exception handling in all tool handlers
    *   Error responses in the API
    *   Logging of errors
*   **Required Actions:**
    *   Review all exception handling code for completeness
    *   Ensure all errors are properly logged with appropriate context
    *   Verify that error responses don't leak sensitive information
    *   Implement consistent error responses across all tools

## Edge Case Testing

### Large PDFs

*   **Status:** Not tested
*   **Required Actions:**
    *   Test with very large PDFs (100+ pages)
    *   Test with PDFs containing large images
    *   Test with PDFs containing complex layouts
    *   Verify memory usage and performance with large files
    *   Document any limitations or recommendations for large files

### Malformed PDFs

*   **Status:** Not tested
*   **Required Actions:**
    *   Test with corrupted PDFs
    *   Test with PDFs missing critical structures
    *   Test with PDFs containing invalid content
    *   Verify that the server handles malformed PDFs gracefully
    *   Ensure proper error messages are returned

### Password-Protected PDFs

*   **Status:** Partially supported
*   **Required Actions:**
    *   Test with password-protected PDFs
    *   Test with different encryption methods
    *   Test with invalid passwords
    *   Verify that all tools properly support the password parameter
    *   Document password handling capabilities and limitations

## Security Recommendations

1. **Run in a Containerized Environment:** Deploy the server in a containerized environment with appropriate resource limits and isolation.

2. **Regular Dependency Updates:** Keep all dependencies, especially PyMuPDF, up-to-date with security patches.

3. **Avoid `--allow-any-path` Flag:** Never use the `--allow-any-path` flag in production or multi-user environments.

4. **Implement Rate Limiting:** Consider implementing rate limiting for API requests to prevent DoS attacks.

5. **Regular Security Audits:** Conduct regular security audits of the codebase, especially after significant changes.

6. **Secure External Dependencies:** Ensure Java and Tesseract are installed from trusted sources and kept updated.

7. **Monitor Resource Usage:** Implement monitoring for CPU, memory, and disk usage to detect potential DoS attacks.

8. **Implement Proper Logging:** Ensure all security-related events are properly logged for auditing purposes.