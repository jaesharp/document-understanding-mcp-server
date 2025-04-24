"""
Fixtures for integration tests.
"""

import pytest
import tempfile
from pathlib import Path
from tests.pdf_generators import create_text_pdf, create_image_pdf


@pytest.fixture(scope="function")
def create_test_env():
    """
    Create a test environment with test PDFs.

    Returns:
        Dictionary with test environment information
    """
    # Create a temporary directory for the test
    with tempfile.TemporaryDirectory() as tmp_dir:
        work_dir = Path(tmp_dir) / "server_test"
        work_dir.mkdir()
        log_dir = work_dir / "logs"
        log_dir.mkdir()
        log_file = log_dir / "server.log"

        # Create a test PDF
        pdf_path = work_dir / "test.pdf"
        create_text_pdf(str(pdf_path))

        # Create an image PDF
        img_pdf_path = work_dir / "image.pdf"
        create_image_pdf(str(img_pdf_path))

        # Return the test environment
        yield {
            "work_dir": work_dir,
            "log_file": log_file,
            "pdf_path": pdf_path,
            "img_pdf_path": img_pdf_path,
        }
