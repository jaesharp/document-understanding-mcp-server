import pytest
import subprocess
from unittest.mock import MagicMock, patch, AsyncMock
from src.document_understanding.extractor import PDFExtractor
import json
import os

# Import the server instance and methods to test/patch
from src.document_understanding import server as pdf_server


# Helper to check Java runtime - useful for table extraction tests
def check_java_runtime():
    """Checks if Java runtime is available."""
    try:
        # Use 'java -version' which prints to stderr
        subprocess.run(
            ["java", "-version"], check=True, capture_output=True, text=True, timeout=5
        )
        return True
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ):
        return False


# Define a fixture for a PDFExtractor instance
@pytest.fixture
def pdf_extractor_instance(mocker):
    """Provides a PDFExtractor instance with mocked dependencies."""
    mock_file_exists = MagicMock(return_value=True)
    mock_doc = MagicMock(spec=fitz.Document)
    mock_doc.page_count = 1
    mock_doc.needs_pass = False

    # Mock _open_pdf to return the mock_doc directly, not a context manager
    mock_pdf_opener = MagicMock(return_value=mock_doc)

    # Mock os.path.exists used internally if not overridden by file_exists_checker
    mocker.patch("os.path.exists", return_value=True)

    extractor = PDFExtractor(
        file_exists_checker=mock_file_exists, pdf_opener=mock_pdf_opener
    )
    # Store mocks on the instance for easy access in tests if needed
    extractor._mock_doc = mock_doc
    extractor._mock_opener = mock_pdf_opener
    extractor._mock_file_exists = mock_file_exists
    return extractor


# Import fitz conditionally for type hints
try:
    import fitz
except ImportError:
    fitz = None  # Keep tests runnable even if fitz isn't installed directly in test env


@pytest.fixture(autouse=True)
def reset_server_state():
    """Reset global state before each test."""
    # Reset may be configured per test or per module as needed


@pytest.fixture
def mock_extractor():
    """Create a mock PDFExtractor instance for testing."""
    mock = MagicMock(spec=PDFExtractor)
    return mock


@pytest.fixture
def any_path_allowed():
    """Patch ALLOW_ANY_PATH to True for testing."""
    with patch("src.document_understanding.server.ALLOW_ANY_PATH", True):
        yield


@pytest.fixture
def search_capability_enabled():
    """Enable search capability for testing."""
    with patch.dict(
        pdf_server.SERVER_CAPABILITIES, {"search_functionality": True}, clear=True
    ):
        yield


@pytest.fixture
def java_capability_enabled():
    """Enable Java runtime capability for testing."""
    with patch.dict(pdf_server.SERVER_CAPABILITIES, {"java_runtime": True}, clear=True):
        yield


@pytest.fixture
def all_capabilities_enabled():
    """Enable all capabilities for testing."""
    with patch.dict(
        pdf_server.SERVER_CAPABILITIES,
        {
            "search_functionality": True,
            "java_runtime": True,
            "experimental_features": True,
        },
        clear=True,
    ):
        yield


# Existing test_pdfs_setup fixture if needed
# You may need to import or reference it from the main conftest.py
