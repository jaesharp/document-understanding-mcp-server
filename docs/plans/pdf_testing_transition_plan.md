# PDF Testing Transition Plan: From Static to Dynamic Test PDFs

## Overview

This document outlines the transition of our test suite from using static PDF files to dynamically generated PDFs. This transition has been completed, with all tests now using dynamically generated PDFs.

## Previous vs. Current Approach

### Previous Approach
- Static PDF files were stored in the `tests/data` directory
- Tests relied on these files being present in the repository
- Difficult to understand what each PDF contained without opening it
- Required committing binary files to the repository

### Current Approach
- All tests use PDFs that are generated dynamically by fixtures in `tests/conftest.py` and `tests/pdf_generators.py`
- All PDF types (text, images, tables, outlines, etc.) are created at test time
- No static PDF files are stored in the repository
- Clear documentation of what each PDF contains in the code for dynamically generated PDFs
- End-to-end tests use the MCP command-line interface to interact with the server

## Implementation

The implementation has been completed with the following steps:

1. Enhanced the existing PDF generation functions in `tests/conftest.py`
2. Added new functions to generate more complex PDFs (tables, outlines, etc.)
3. Created a dedicated `tests/pdf_generators.py` module for PDF generation functions
4. Updated all test fixtures to use these dynamically generated PDFs
5. Implemented new end-to-end tests using the MCP command-line interface

## Completed Work

1. ✅ Updated all tests to use dynamically generated PDFs
2. ✅ Removed static PDF files from the repository
3. ✅ Ensured all test scripts use the same PDF generation approach for consistency
4. ✅ Implemented new end-to-end tests using the MCP command-line interface
5. ✅ Created a dedicated module for PDF generation functions

## Benefits

### Improved Developer Experience
- No need to commit binary files to the repository
- Clear understanding of test PDF contents from the code
- Easier to create new test PDFs for specific test cases
- Reduced repository size

### Better Test Maintainability
- All test data is generated programmatically
- PDF generation code is centralized and reusable
- Tests are more self-contained and portable
- Easier to understand what's being tested

### Future Improvements
- Further enhance PDF generation capabilities for more complex documents
- Consider moving to a more declarative approach for defining test PDFs
- Improve performance by caching generated PDFs during test runs
- Add more documentation about the available PDF types

## Implementation Details

### PDF Generation Functions

The implementation uses several PDF generation functions in `tests/conftest.py`:

#### 1. Basic PDF Generation
```python
def create_text_pdf(path: Path, text: str = "Test content for text extraction."):
    """Creates a simple 1-page PDF with text."""
    c = canvas.Canvas(str(path), pagesize=letter)
    textobject = c.beginText(inch, 10 * inch)
    textobject.textLine(text)
    c.drawText(textobject)
    c.save()

def create_empty_pdf(path: Path):
    """Creates a 0-page PDF."""
    c = canvas.Canvas(str(path), pagesize=letter)
    # No pages added
    c.save()
```

#### 2. Complex PDF Generation
```python
def create_table_pdf(path: Path):
    """Creates a simple 1-page PDF with a table."""
    doc = SimpleDocTemplate(str(path), pagesize=letter)
    story = []

    data = [
        ['Header 1', 'Header 2', 'Header 3'],
        ['A1', 'B1', 'C1'],
        ['A2', 'B2', 'C2'],
        ['A3', 'B3', 'C3']
    ]

    # Create table with styling
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(table)
    doc.build(story)
```

### Test Fixture

The main test fixture in `tests/conftest.py` creates all the necessary PDFs:

```python
@pytest.fixture
def test_pdfs_setup(tmp_path):
    """Setup test PDFs in a temporary directory."""
    # Create base temp directory
    base_temp_dir = tmp_path / "pdfs"
    base_temp_dir.mkdir(exist_ok=True)

    # Dictionary to store paths to generated PDFs
    paths_dict = {}

    # Generate different types of PDFs
    paths_dict["text"] = base_temp_dir / "text_doc.pdf"
    create_text_pdf(paths_dict["text"])

    paths_dict["empty"] = base_temp_dir / "empty_doc.pdf"
    create_empty_pdf(paths_dict["empty"])

    paths_dict["table"] = base_temp_dir / "table_doc.pdf"
    create_table_pdf(paths_dict["table"])

    # Return dictionary of paths
    return paths_dict
```

## Conclusion

The transition to dynamically generated PDFs has been completed. All tests now use PDFs that are generated at test time, and no static PDF files are stored in the repository. This approach has improved maintainability, reduced repository size, and made all tests more self-contained and portable.

## Current Status

- [x] Basic PDF generation fixtures implemented
- [x] Unit tests updated to use generated PDFs
- [x] Integration tests updated to use generated PDFs
- [x] E2E tests updated to use generated PDFs
- [x] Static test PDFs removed from repository

**Status:** ✅ Completed
