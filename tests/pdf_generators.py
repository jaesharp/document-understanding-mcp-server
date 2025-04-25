"""
PDF Generation Utilities for Testing

This module provides functions for generating various types of PDF files for testing purposes.
It can be used both for creating static test PDFs and for dynamically generating PDFs during tests.

Usage:
    1. Static PDF creation: Used by create_static_test_pdfs.py to generate PDFs in tests/data
    2. Dynamic PDF creation: Used by conftest.py to generate PDFs in temporary directories for tests
"""

import os
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from PIL import Image
import tempfile
import fitz
from typing import Optional


def create_text_pdf(path: Path, text: str = "This is a test PDF with only text."):
    """
    Creates a simple text PDF.

    Args:
        path: Path where the PDF will be saved
        text: Text content to include in the PDF
    """
    c = canvas.Canvas(str(path), pagesize=letter)
    textobject = c.beginText(inch, 10 * inch)
    textobject.textLine(text)
    c.drawText(textobject)
    c.save()


def create_multipage_text_pdf(path: Path, num_pages: int = 2):
    """
    Creates a multi-page text PDF.

    Args:
        path: Path where the PDF will be saved
        num_pages: Number of pages to create
    """
    c = canvas.Canvas(str(path), pagesize=letter)

    for i in range(num_pages):
        textobject = c.beginText(inch, 10 * inch)
        textobject.textLine(f"Page {i+1}: Text Document")
        textobject.textLine(f"This is page {i+1} of {num_pages}.")
        c.drawText(textobject)

        if i < num_pages - 1:  # Don't call showPage after the last page
            c.showPage()

    c.save()


def create_image_pdf(
    path: Path,
    image_path: Optional[Path] = None,
    text: str = "This PDF has text and an image.",
):
    """
    Creates a PDF with text and an image.

    Args:
        path: Path where the PDF will be saved
        image_path: Path to an image to include (if None, creates a simple image)
        text: Text content to include in the PDF
    """
    # If no image path provided or image doesn't exist, create a simple image
    if image_path is None or not Path(image_path).exists():
        # Create a temporary image
        img_width, img_height = int(letter[0] * 0.2), int(
            letter[1] * 0.1
        )  # Small image
        img = Image.new("RGB", (img_width, img_height), color="purple")

        # If image_path was provided, save there
        if image_path:
            img.save(image_path)
            img_to_use = image_path
        else:
            # Otherwise use a temporary file
            with tempfile.NamedTemporaryFile(
                suffix=".png", delete=False
            ) as temp_img_file:
                img.save(temp_img_file.name, format="PNG")
                img_to_use = temp_img_file.name
    else:
        img_to_use = image_path

    # Create the PDF using PyMuPDF
    doc = fitz.open()
    page = doc.new_page(width=letter[0], height=letter[1])

    # Add text
    page.insert_text((inch, inch), text, fontsize=12)

    # Add image
    try:
        # Define the rectangle for the image
        rect = fitz.Rect(inch, 2 * inch, 3 * inch, 4 * inch)
        # Insert the image
        page.insert_image(rect, filename=img_to_use)
    finally:
        # Clean up temporary file if we created one
        if image_path is None and img_to_use != image_path:
            try:
                os.remove(img_to_use)
            except:
                pass

    # Save the PDF
    doc.save(str(path))
    doc.close()


def create_drawing_pdf(path: Path, text: str = "This PDF has text and drawings."):
    """
    Creates a PDF with text and vector drawings.

    Args:
        path: Path where the PDF will be saved
        text: Text content to include in the PDF
    """
    c = canvas.Canvas(str(path), pagesize=letter)

    # Draw text
    textobject = c.beginText(inch, 10 * inch)
    textobject.textLine(text)
    c.drawText(textobject)

    # Draw a rectangle
    c.setStrokeColorRGB(0, 0, 1)  # Blue
    c.rect(inch, 8 * inch, 2 * inch, 1 * inch, stroke=1, fill=0)

    # Draw a line
    c.setStrokeColorRGB(1, 0, 0)  # Red
    c.line(inch, 7.5 * inch, 3 * inch, 7.5 * inch)

    c.save()


def create_all_elements_pdf(
    path: Path,
    image_path: Optional[Path] = None,
    text: str = "Text, image, and drawing.",
):
    """
    Creates a PDF with text, image, and vector drawings.

    Args:
        path: Path where the PDF will be saved
        image_path: Path to an image to include (if None, creates a simple image)
        text: Text content to include in the PDF
    """
    # If no image path provided or image doesn't exist, create a simple image
    if image_path is None or not Path(image_path).exists():
        # Create a temporary image
        img_width, img_height = int(letter[0] * 0.2), int(
            letter[1] * 0.1
        )  # Small image
        img = Image.new("RGB", (img_width, img_height), color="green")

        # If image_path was provided, save there
        if image_path:
            img.save(image_path)
            img_to_use = image_path
        else:
            # Otherwise use a temporary file
            with tempfile.NamedTemporaryFile(
                suffix=".png", delete=False
            ) as temp_img_file:
                img.save(temp_img_file.name, format="PNG")
                img_to_use = temp_img_file.name
    else:
        img_to_use = image_path

    # Create the PDF
    c = canvas.Canvas(str(path), pagesize=letter)

    # Draw text
    textobject = c.beginText(inch, 10 * inch)
    textobject.textLine(text)
    c.drawText(textobject)

    # Draw image
    try:
        img_reader = ImageReader(img_to_use)
        img_width, img_height = img_reader.getSize()
        aspect = img_height / float(img_width)
        c.drawImage(
            img_to_use, inch, 8 * inch, width=1 * inch, height=(1 * aspect * inch)
        )
    finally:
        # Clean up temporary file if we created one
        if image_path is None and img_to_use != image_path:
            try:
                os.remove(img_to_use)
            except:
                pass

    # Draw rectangle
    c.setStrokeColorRGB(0, 1, 0)  # Green
    c.rect(3 * inch, 8 * inch, 1 * inch, 0.5 * inch, stroke=1, fill=0)

    c.save()


def create_empty_pdf(path: Path):
    """
    Creates an empty PDF (0 pages).

    Args:
        path: Path where the PDF will be saved
    """
    c = canvas.Canvas(str(path), pagesize=letter)
    # No pages added
    c.save()


def create_table_pdf(path: Path):
    """
    Creates a PDF with a formatted table.

    Args:
        path: Path where the PDF will be saved
    """
    doc = SimpleDocTemplate(str(path), pagesize=letter)
    story = []

    data = [
        ["Header 1", "Header 2", "Header 3"],
        ["A1", "B1", "C1"],
        ["A2", "B2", "C2"],
        ["A3", "B3", "C3"],
    ]

    # Basic table style
    style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ]
    )

    # Create table
    table = Table(data)
    table.setStyle(style)
    story.append(table)

    doc.build(story)


def create_outline_pdf(path: Path):
    """
    Creates a PDF with a nested outline (TOC/Bookmarks).

    Args:
        path: Path where the PDF will be saved
    """
    doc = fitz.open()  # Create new empty doc

    # Add a few pages
    for i in range(6):
        page = doc.new_page()
        page.insert_text((72, 72), f"This is page {i + 1}")

    # Define the Table of Contents structure
    # Format: [level, title, page_number_0_based]
    toc = [
        [1, "Chapter 1", 0],
        [2, "Section 1.1", 1],
        [3, "Subsection 1.1.1", 2],
        [2, "Section 1.2", 3],
        [1, "Chapter 2", 4],
        [2, "Section 2.1", 5],
    ]

    # Set the TOC in the document
    doc.set_toc(toc)
    doc.save(str(path))
    doc.close()


def create_encrypted_pdf(
    path: Path, password: str = "testpassword", text: str = "Encrypted PDF content."
):
    """
    Creates a password-protected PDF.

    Args:
        path: Path where the PDF will be saved
        password: Password to protect the PDF
        text: Text content to include in the PDF
    """
    doc = fitz.open()  # Create new empty doc
    page = doc.new_page()
    page.insert_text((72, 72), text)

    # Encryption settings
    encrypt_options = {
        "owner_pw": "owner",  # Owner password
        "user_pw": password,  # User password
        "encryption": fitz.PDF_ENCRYPT_AES_256,  # Strong encryption
    }

    doc.save(str(path), **encrypt_options)
    doc.close()


def create_bbox_issue_pdf(path: Path):
    """
    Creates a PDF that triggers the bounding box conversion issue in PyMuPDF.

    This PDF contains specific image formats and structures that are known to cause
    issues with PyMuPDF's get_image_rects() function, resulting in the error:
    "Unrecognised args for constructing Pixmap".

    Args:
        path: Path where the PDF will be saved
    """
    # First create a PDF with ReportLab
    temp_path = str(path) + ".temp.pdf"
    c = canvas.Canvas(temp_path, pagesize=letter)
    width, height = letter

    # Add a title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(inch, height - inch, "Test PDF for Bounding Box Conversion Issue")

    # Add some text blocks
    c.setFont("Helvetica", 12)
    c.drawString(
        inch,
        height - 2 * inch,
        "This PDF contains images that trigger the bounding box conversion issue.",
    )
    c.drawString(
        inch,
        height - 2.5 * inch,
        "When processed with PyMuPDF, it will generate warnings about image bounding boxes.",
    )

    # Create a test image with specific characteristics
    img_width, img_height = 300, 150
    img = Image.new("RGB", (img_width, img_height), color="red")

    # Add a gradient pattern that might trigger the issue
    for y in range(img_height):
        for x in range(img_width):
            r = int(255 * x / img_width)
            g = int(255 * y / img_height)
            b = int(255 * (x + y) / (img_width + img_height))
            img.putpixel((x, y), (r, g, b))

    # Save to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_img_file:
        img.save(temp_img_file.name, format="JPEG", quality=85)
        img_path = temp_img_file.name

    # Add the image to the PDF
    try:
        c.drawImage(img_path, inch, height - 4 * inch, width=4 * inch, height=inch)

        # Add some drawings
        c.setStrokeColor(colors.blue)
        c.rect(inch, height - 5 * inch, 3 * inch, 0.5 * inch)

        c.setStrokeColor(colors.red)
        c.line(inch, height - 5.5 * inch, 4 * inch, height - 6 * inch)

        # Save the PDF
        c.save()
    finally:
        # Clean up the temporary image file
        try:
            os.remove(img_path)
        except:
            pass

    # Now use PyMuPDF to add specific image structures that trigger the issue
    doc = fitz.open(temp_path)

    # Add a second page
    page = doc.new_page()

    # Add text to the second page
    page.insert_text((inch, inch), "Second page with more test content")

    # Add an image using PyMuPDF's methods
    # This creates a different image structure than ReportLab
    rect = fitz.Rect(inch, 2 * inch, 5 * inch, 4 * inch)
    try:
        # Create another test image
        img2 = Image.new("RGB", (400, 200), color="blue")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_img_file2:
            img2.save(temp_img_file2.name, format="PNG")
            img_path2 = temp_img_file2.name

        # Insert the image
        page.insert_image(rect, filename=img_path2)
    except Exception as e:
        print(f"Error inserting image: {e}")
    finally:
        # Clean up
        try:
            os.remove(img_path2)
        except:
            pass

    # Save the final PDF
    doc.save(str(path))
    doc.close()

    # Clean up the temporary PDF
    try:
        os.remove(temp_path)
    except:
        pass
