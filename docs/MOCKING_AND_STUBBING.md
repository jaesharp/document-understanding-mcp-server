# Mocking and Stubbing for Document Understanding MCP Server

This document provides guidance on mocking and stubbing approaches used in the `document-understanding-mcp-server` project for testing. These patterns are based on actual practices in the codebase and should be followed for consistency.

## PDF Document Mocking

### PyMuPDF Document Mocking

The project uses PyMuPDF (`fitz`) for PDF processing. For testing, we mock the `fitz.Document` class and its methods using dependency injection or direct patching:

```python
# Approach 1: Create a mock document and inject it via _open_pdf
@pytest.fixture
def mock_extractor(mocker):
    """Fixture to create a PDFExtractor with mocked dependencies."""
    mock_file_exists = MagicMock(return_value=True)
    mock_doc = MagicMock(spec=fitz.Document)
    mock_doc.page_count = 2  # Default page count
    mock_doc.needs_pass = False  # Important for password testing

    # Create a context manager mock for the document
    mock_opener_cm = MagicMock()
    mock_opener_cm.__enter__.return_value = mock_doc
    mock_opener_cm.__exit__.return_value = None
    mock_pdf_opener = MagicMock(return_value=mock_opener_cm)

    extractor = PDFExtractor(
        file_exists_checker=mock_file_exists,
        pdf_opener=mock_pdf_opener,
        capabilities={"tesseract_ocr": False}  # Default to no OCR unless overridden
    )
    # Attach mocks for easy access in tests
    extractor._mock_doc = mock_doc
    extractor._mock_pdf_opener = mock_pdf_opener
    extractor._mock_file_exists = mock_file_exists
    return extractor

# Approach 2: Patch the _open_pdf method to return a mock document
def test_extract_layout_page_error(mocker, test_pdfs_setup):
    extractor = PDFExtractor()
    pdf_path = str(test_pdfs_setup["text"])

    # Mock the page methods to simulate an error
    mock_page = MagicMock(spec=fitz.Page)
    mock_page.get_text.side_effect = Exception("Layout Text Failed")
    mock_page.get_drawings.return_value = []
    mock_page.get_images.return_value = []

    # Mock document and page loading
    mock_doc = MagicMock(spec=fitz.Document)
    mock_doc.page_count = 1
    mock_doc.needs_pass = False
    mock_doc.load_page.return_value = mock_page
    mocker.patch.object(extractor, '_open_pdf', return_value=mock_doc)
    mocker.patch.object(extractor, '_file_exists', return_value=True)

    # Test with the mocked document
    results = extractor.extract_layout(pdf_path, pages_str="1")
    # Assertions...
```

### Mocking Specific Extractor Methods

For testing higher-level functions, we often mock specific implementation methods rather than the entire extractor:

```python
def test_extract_tables_tabula_error(mocker, test_pdfs_setup):
    """Test extract_tables handles errors from tabula.read_pdf."""
    # Mock the implementation method directly
    mock_impl = mocker.patch(
        'src.document_understanding.extractor.extractor._extract_tables_impl',
        side_effect=ValueError("Table extraction failed for PDF 'path/table.pdf': Tabula Crashed")
    )

    # Use a real extractor instance with the mocked implementation
    extractor = PDFExtractor()
    pdf_path = str(test_pdfs_setup["table"])

    with pytest.raises(ValueError, match=r"Table extraction failed for PDF.*Tabula Crashed"):
        extractor.extract_tables(pdf_path, pages_spec="1")

    # Assert the implementation function was called with expected arguments
    mock_impl.assert_called_once_with(extractor, pdf_path=pdf_path, pages_spec="1", password=None)
```

## File System Mocking

The project uses dependency injection for file system operations rather than directly patching global functions. This approach provides better isolation and testability:

```python
# Approach 1: Inject mocks via constructor
def test_extract_content_file_not_found(mocker):
    """Test FileNotFoundError when file doesn't exist."""
    # Create a mock for file existence check
    mock_file_exists = MagicMock(return_value=False)

    # Inject the mock into the extractor
    extractor = PDFExtractor(file_exists_checker=mock_file_exists)

    with pytest.raises(FileNotFoundError):
        extractor.extract_content("non_existent.pdf", None)

    mock_file_exists.assert_called_once_with("non_existent.pdf")

# Approach 2: Patch instance methods
def test_file_not_found(mocker):
    extractor = PDFExtractor()
    # Patch the instance method directly
    mocker.patch.object(extractor, '_file_exists', return_value=False)

    with pytest.raises(FileNotFoundError):
        extractor.extract_metadata("non_existent.pdf")
```

## External Dependencies Mocking

### Java Runtime and Tabula Mocking

For testing table extraction which depends on Java and tabula-py:

```python
def test_extract_tables_impl_java_not_found_error(mock_extractor, mocker):
    """Test _extract_tables_impl raises TableExtractionError if Java runtime is missing."""
    # Mock tabula.read_pdf to simulate Java missing
    mock_file_error = FileNotFoundError("[Errno 2] No such file or directory: 'java': 'java'")
    mocker.patch('tabula.read_pdf', side_effect=mock_file_error)

    with pytest.raises(TableExtractionError, match="Table extraction requires Java runtime"):
        table_extraction._extract_tables_impl(mock_extractor, "dummy.pdf", pages_spec="1")
```

### Tesseract OCR Mocking

For testing OCR functionality which depends on pytesseract:

```python
def test_init_with_ocr(mocker):
    """Test PDFExtractor initializes OCR runner when capability is True."""
    # Mock pytesseract globally
    mock_pytesseract = MagicMock()
    mocker.patch.dict(sys.modules, {'pytesseract': mock_pytesseract})

    # Mock the logger
    mock_logger = mocker.patch('src.document_understanding.extractor.extractor.logger')

    # Instantiate with OCR capability enabled
    extractor = PDFExtractor(capabilities={"tesseract_ocr": True})

    assert extractor.capabilities.get("tesseract_ocr") is True
    assert extractor._ocr_runner is not None
    mock_logger.debug.assert_any_call("Tesseract OCR runner initialized.")
```

## Testing Error Handling

The project extensively tests error handling paths. Here's how to test different error scenarios:

```python
# Test specific error types
def test_open_pdf_document_handles_auth_failure_return_val(mocker):
    """Test _open_pdf_document handles authentication failure."""
    extractor = PDFExtractor()
    mock_internal_open = mocker.patch.object(extractor, '_open_pdf')

    # Configure mock document for password failure
    mock_doc = MagicMock(spec=fitz.Document)
    mock_doc.needs_pass = True
    mock_doc.authenticate.return_value = 0  # Simulate failed auth
    mock_internal_open.return_value = mock_doc

    with pytest.raises(PDFPasswordError, match="Incorrect password provided"):
        extractor._open_pdf_document("dummy_encrypted.pdf", password="wrong")

# Test error handling in page processing loops
def test_extract_content_page_loop_error(mocker, test_pdfs_setup):
    """Test error handling within the page processing loop."""
    extractor = PDFExtractor()
    pdf_path = Path(test_pdfs_setup["text"].parent) / "text_doc_2pages_for_loop_error.pdf"

    # Create a test PDF
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.drawString(inch, 10 * inch, "Page 1 Content")
    c.showPage()
    c.drawString(inch, 10 * inch, "Page 2 Content")
    c.save()

    # Mock document with one good page and one page that raises an error
    mock_doc = MagicMock(spec=fitz.Document)
    mock_doc.page_count = 2

    mock_page_0 = MagicMock(spec=fitz.Page)
    mock_page_0.number = 0
    mock_page_0.get_text.return_value = "Page 1 Mock Text"

    mock_page_1 = MagicMock(spec=fitz.Page)
    mock_page_1.number = 1
    mock_page_1.get_text.side_effect = Exception("Simulated Page 2 Text Extraction Failed")

    # Configure load_page to return different pages
    mock_doc.load_page.side_effect = lambda idx: mock_page_0 if idx == 0 else mock_page_1

    # Patch _open_pdf_document
    with patch.object(extractor, '_open_pdf_document', return_value=mock_doc):
        results = extractor.extract_content(str(pdf_path), "1,2")

    # Verify results contain success for page 1 and error for page 2
    assert len(results) == 2
    assert results[0]["page"] == 1
    assert "error" not in results[0]
    assert results[1]["page"] == 2
    assert "error" in results[1]
```

## Testing Dynamically Generated PDFs

The test suite uses dynamically generated PDFs for all tests. No static PDF files are stored in the repository. The test fixtures in `tests/conftest.py` generate all necessary test PDFs at runtime.

Example of how to use the dynamically generated PDFs in tests:

```python
def test_extract_content_success(test_pdfs_setup):
    """Test successful basic content extraction."""
    extractor = PDFExtractor()
    # Use a PDF from the test_pdfs_setup fixture
    pdf_path = str(test_pdfs_setup["text"])

    results = extractor.extract_content(pdf_path, pages_str=None)

    assert len(results) == 1
    assert results[0]["page"] == 1
    assert "Test" in results[0]["content"]
    assert "error" not in results[0]
```

The `test_pdfs_setup` fixture in `tests/conftest.py` provides these PDF types:
- `text`: Simple text document
- `image`: Document with embedded image
- `drawings_only`: Document with vector drawings
- `all_elements`: Document with text, images, and drawings
- `encrypted`: Password-protected document (password: "testpassword")
- `empty`: Empty document (0 pages)
- `table`: Document with a formatted table
- `outline`: Document with bookmarks/outline
- `non_existent`: Path to a non-existent file (for testing error handling)

## Conditional Test Skipping

For tests that depend on external dependencies like Java:

```python
# Function to check for Java runtime
def check_java_runtime():
    try:
        import subprocess
        subprocess.run(["java", "-version"], check=True, capture_output=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

java_present = check_java_runtime()

# Skip test if Java is not available
@pytest.mark.skipif(not java_present, reason="Java runtime not found, skipping natural table extraction test.")
def test_extract_tables_natural(test_pdfs_setup):
    """Test extract_tables against a real PDF with known tables."""
    extractor = PDFExtractor()
    pdf_path = str(test_pdfs_setup["table"])

    results = extractor.extract_tables(pdf_path, pages_spec="1")

    # Assertions...
```