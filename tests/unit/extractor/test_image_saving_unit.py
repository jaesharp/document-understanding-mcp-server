"""Unit tests for the image saving functionality in the extract_images tool."""

import os
import base64
import pytest
from unittest.mock import MagicMock, patch
from document_understanding.extractor.extractor import PDFExtractor


@pytest.mark.parametrize("enable_save_images", ["true", "false"])
def test_extract_images_save_to_files(mocker, tmp_path, enable_save_images):
    """Test saving images to files with feature flag control."""
    # Create output directory
    output_dir = str(tmp_path / "images")
    os.makedirs(output_dir, exist_ok=True)

    # Setup mock environment
    mocker.patch.dict(
        os.environ,
        {
            "ENABLE_SAVE_IMAGES_TO_FILES": enable_save_images,
            "SAFE_OUTPUT_DIRECTORIES": output_dir,
            "ALLOW_ANY_PATH": "false",
        },
    )

    # Setup mock document and image data
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_images.return_value = [(1, 0, 0, 0, 0, 0, 0)]  # xref, ...

    # Mock image data with binary content
    mock_image_data = {"image": b"fake_image_data", "ext": "png"}
    mock_doc.extract_image.return_value = mock_image_data
    mock_doc.load_page.return_value = mock_page
    mock_doc.page_count = 1

    # Create extractor and patch methods
    extractor = PDFExtractor(capabilities={"tesseract_ocr": False})
    mocker.patch.object(extractor, "_open_pdf_document", return_value=mock_doc)
    mocker.patch.object(extractor, "check_file_exists", return_value=True)

    # Create output directory
    output_dir = str(tmp_path / "images")

    # Run extraction with output directory
    results = extractor.extract_images(
        "dummy.pdf", pages_str="1", include_data=True, output_directory=output_dir
    )

    # Check results
    assert len(results) == 1

    # Check if file was saved based on feature flag
    expected_file_path = os.path.join(output_dir, "image_p1_x1.png")
    if enable_save_images == "true":
        assert os.path.exists(expected_file_path)
        assert "file_path" in results[0]
        assert results[0]["file_path"] == expected_file_path

        # Verify file contents
        with open(expected_file_path, "rb") as f:
            assert f.read() == b"fake_image_data"
    else:
        assert "file_path" not in results[0]


@pytest.mark.parametrize("allow_any_path", ["true", "false"])
def test_extract_images_path_security(mocker, tmp_path, allow_any_path):
    """Test path security restrictions for saving images."""
    # Setup safe directories and test directories
    safe_dir = str(tmp_path / "safe")
    unsafe_dir = str(tmp_path / "unsafe")

    # Setup mock environment
    mocker.patch.dict(
        os.environ,
        {
            "ENABLE_SAVE_IMAGES_TO_FILES": "true",
            "ALLOW_ANY_PATH": allow_any_path,
            "SAFE_OUTPUT_DIRECTORIES": safe_dir,
        },
    )

    # Setup mock document and image data
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_images.return_value = [(1, 0, 0, 0, 0, 0, 0)]  # xref, ...
    mock_image_data = {"image": b"test_data", "ext": "png"}
    mock_doc.extract_image.return_value = mock_image_data
    mock_doc.load_page.return_value = mock_page
    mock_doc.page_count = 1

    # Create extractor and patch methods
    extractor = PDFExtractor(capabilities={"tesseract_ocr": False})
    mocker.patch.object(extractor, "_open_pdf_document", return_value=mock_doc)
    mocker.patch.object(extractor, "check_file_exists", return_value=True)

    # Test with safe directory
    safe_results = extractor.extract_images(
        "dummy.pdf", pages_str="1", include_data=True, output_directory=safe_dir
    )

    # Test with unsafe directory
    unsafe_results = extractor.extract_images(
        "dummy.pdf", pages_str="1", include_data=True, output_directory=unsafe_dir
    )

    # Check results based on security settings
    safe_file_path = os.path.join(safe_dir, "image_p1_x1.png")
    unsafe_file_path = os.path.join(unsafe_dir, "image_p1_x1.png")

    # Safe directory should always work if feature is enabled
    assert "file_path" in safe_results[0]
    assert safe_results[0]["file_path"] == safe_file_path
    assert os.path.exists(safe_file_path)

    # Unsafe directory should only work if ALLOW_ANY_PATH is true
    if allow_any_path == "true":
        assert "file_path" in unsafe_results[0]
        assert unsafe_results[0]["file_path"] == unsafe_file_path
        assert os.path.exists(unsafe_file_path)
    else:
        assert "file_path" not in unsafe_results[0]
        assert not os.path.exists(unsafe_dir)


def test_extract_images_directory_creation_error(mocker):
    """Test error handling when directory creation fails."""
    # Setup mock environment
    mocker.patch.dict(os.environ, {"ENABLE_SAVE_IMAGES_TO_FILES": "true"})

    # Setup mock document and image data
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_images.return_value = [(1, 0, 0, 0, 0, 0, 0)]  # xref, ...
    mock_doc.load_page.return_value = mock_page
    mock_doc.page_count = 1

    # Create extractor and patch methods
    extractor = PDFExtractor(capabilities={"tesseract_ocr": False})
    mocker.patch.object(extractor, "_open_pdf_document", return_value=mock_doc)
    mocker.patch.object(extractor, "check_file_exists", return_value=True)

    # Mock os.makedirs to raise an exception
    with patch("os.makedirs", side_effect=PermissionError("Permission denied")):
        # Run extraction with output directory that will fail to create
        results = extractor.extract_images(
            "dummy.pdf", pages_str="1", output_directory="/nonexistent/directory"
        )

    # Check that extraction still works but file_path is not included
    assert len(results) == 1
    assert "file_path" not in results[0]
