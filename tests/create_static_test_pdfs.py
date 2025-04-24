#!/usr/bin/env python3
"""
Create Static Test PDFs

This script generates static PDF files in the tests/data directory for use in integration tests.
These files are not committed to the repository (they're in .gitignore) but are created
when needed for testing.

Usage:
    python tests/create_static_test_pdfs.py
"""

from pathlib import Path
from pdf_generators import (
    create_multipage_text_pdf,
    create_image_pdf,
    create_empty_pdf,
    create_table_pdf,
    create_outline_pdf,
    create_encrypted_pdf,
)

# Directory for static test PDFs
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def main():
    """Create all static test PDFs in the data directory."""
    print(f"Creating static test PDFs in {DATA_DIR}")

    # Create text PDF with multiple pages
    text_pdf_path = DATA_DIR / "text_doc.pdf"
    create_multipage_text_pdf(text_pdf_path)
    print(f"Created: {text_pdf_path}")

    # Create image PDF
    image_pdf_path = DATA_DIR / "image_doc.pdf"
    create_image_pdf(image_pdf_path, text="Page 1: Image Text")
    print(f"Created: {image_pdf_path}")

    # Create empty PDF
    empty_pdf_path = DATA_DIR / "empty_doc.pdf"
    create_empty_pdf(empty_pdf_path)
    print(f"Created: {empty_pdf_path}")

    # Create table PDF
    table_pdf_path = DATA_DIR / "table_doc.pdf"
    create_table_pdf(table_pdf_path)
    print(f"Created: {table_pdf_path}")

    # Create outline PDF
    outline_pdf_path = DATA_DIR / "outline_doc.pdf"
    create_outline_pdf(outline_pdf_path)
    print(f"Created: {outline_pdf_path}")

    # Create encrypted PDF
    encrypted_pdf_path = DATA_DIR / "encrypted_doc.pdf"
    create_encrypted_pdf(encrypted_pdf_path)
    print(f"Created: {encrypted_pdf_path} (Password: 'testpassword')")

    print("\nAll static test PDFs created successfully.")


if __name__ == "__main__":
    main()
