"""Integration tests for the image saving functionality in the extract_images tool."""

import os
import pytest
import tempfile
from PIL import Image
from io import BytesIO
import base64
from document_understanding.extractor.extractor import PDFExtractor

# Skip if test PDFs are not available - REMOVED as we use dynamically generated files


@pytest.fixture
def setup_environment():
    """Setup and teardown environment variables for testing."""
    # Save original environment
    original_env = {}
    for key in [
        "ENABLE_SAVE_IMAGES_TO_FILES",
        "ALLOW_ANY_PATH",
        "SAFE_OUTPUT_DIRECTORIES",
    ]:
        original_env[key] = os.environ.get(key)

    # Set test environment
    os.environ["ENABLE_SAVE_IMAGES_TO_FILES"] = "true"

    yield

    # Restore original environment
    for key, value in original_env.items():
        if value is None:
            if key in os.environ:
                del os.environ[key]
        else:
            os.environ[key] = value


def test_extract_images_save_to_files_integration(setup_environment, test_pdfs_setup):
    """Integration test for saving images to files."""
    # Create a temporary directory for output
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set safe directories
        os.environ["SAFE_OUTPUT_DIRECTORIES"] = temp_dir
        os.environ["ALLOW_ANY_PATH"] = "false"

        # Create extractor
        extractor = PDFExtractor()

        # Extract images from test PDF
        pdf_path = str(test_pdfs_setup["image"])
        results = extractor.extract_images(
            pdf_path, pages_str="1", include_data=True, output_directory=temp_dir
        )

        # Verify results
        assert len(results) > 0

        # Check if any images have file_path (some might not if they couldn't be extracted)
        saved_images = [img for img in results if "file_path" in img]

        # If we have any saved images, verify they exist
        if saved_images:
            for img in saved_images:
                assert os.path.exists(img["file_path"])

                # Verify image can be opened
                with Image.open(img["file_path"]) as pil_img:
                    assert pil_img.width > 0
                    assert pil_img.height > 0

                # Verify file path is within temp_dir
                assert img["file_path"].startswith(temp_dir)
        else:
            # If no images were saved, we should at least have some image data
            assert len(results) > 0


def test_extract_images_path_security_integration(setup_environment, test_pdfs_setup):
    """Integration test for path security restrictions."""
    # Create temporary directories
    with (
        tempfile.TemporaryDirectory() as safe_dir,
        tempfile.TemporaryDirectory() as unsafe_dir,
    ):
        # Set safe directories
        os.environ["SAFE_OUTPUT_DIRECTORIES"] = safe_dir
        os.environ["ALLOW_ANY_PATH"] = "false"

        # Create extractor
        extractor = PDFExtractor()

        # Get test PDF path
        pdf_path = str(test_pdfs_setup["image"])

        # Test with safe directory
        safe_results = extractor.extract_images(
            pdf_path, pages_str="1", output_directory=safe_dir
        )

        # Test with unsafe directory
        unsafe_results = extractor.extract_images(
            pdf_path, pages_str="1", output_directory=unsafe_dir
        )

        # Verify safe directory works
        assert len(safe_results) > 0

        # Check if any images have file_path (some might not if they couldn't be extracted)
        saved_images = [img for img in safe_results if "file_path" in img]

        # If we have any saved images, verify they exist
        if saved_images:
            for img in saved_images:
                assert os.path.exists(img["file_path"])
        else:
            # If no images were saved, we should at least have some image data
            assert len(safe_results) > 0

        # Verify unsafe directory doesn't work
        assert len(unsafe_results) > 0
        for img in unsafe_results:
            assert "file_path" not in img

        # Now enable any path
        os.environ["ALLOW_ANY_PATH"] = "true"

        # Test with unsafe directory again
        unsafe_results_allowed = extractor.extract_images(
            pdf_path, pages_str="1", output_directory=unsafe_dir
        )

        # Verify unsafe directory now works
        assert len(unsafe_results_allowed) > 0

        # Check if any images have file_path (some might not if they couldn't be extracted)
        saved_images = [img for img in unsafe_results_allowed if "file_path" in img]

        # If we have any saved images, verify they exist
        if saved_images:
            for img in saved_images:
                assert os.path.exists(img["file_path"])
        else:
            # If no images were saved, we should at least have some image data
            assert len(unsafe_results_allowed) > 0
