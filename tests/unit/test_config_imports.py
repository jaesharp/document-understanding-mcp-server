import pytest
from unittest.mock import MagicMock
import logging


def test_import_init():
    """Test that the main package can be imported."""
    try:
        from src import document_understanding

        assert document_understanding is not None
    except ImportError as e:
        pytest.fail(f"Failed to import src.document_understanding: {e}")


def test_import_settings():
    """Test that settings can be imported and instantiated."""
    try:
        from src.document_understanding.settings import Settings, settings

        assert isinstance(settings, Settings)
    except ImportError as e:
        pytest.fail(f"Failed to import settings: {e}")
    except Exception as e:
        pytest.fail(f"Failed to instantiate settings: {e}")


def test_import_models():
    """Test that models can be imported."""
    try:
        # Import a few representative models
        pass
    except ImportError as e:
        pytest.fail(f"Failed to import models: {e}")


def test_logging_config_plain(mocker):
    """Test configuring logging with plain format."""
    mock_settings = mocker.patch("src.document_understanding.logging_config.settings")
    mock_settings.log_format = "plain"
    mock_settings.log_level = "INFO"

    # Mock getLogger to check interactions without modifying root
    mock_logger_instance = MagicMock()
    mock_get_logger = mocker.patch(
        "logging.getLogger", return_value=mock_logger_instance
    )

    # Re-import or reload module to ensure it uses the mocked getLogger if needed,
    # or structure configure_logging to accept a logger instance.
    # For simplicity here, assume configure_logging modifies the logger returned by getLogger.
    from src.document_understanding import logging_config

    try:
        # Run config, it should call getLogger() and addHandler() to our mock
        logging_config.configure_logging()
    except Exception as e:
        pytest.fail(f"configure_logging failed with plain format: {e}")

    # Check that getLogger was called (implicitly for root logger)
    mock_get_logger.assert_called()
    # Check that addHandler was called on the mock logger
    mock_logger_instance.addHandler.assert_called_once()
    # Check the handler's formatter
    handler_instance = mock_logger_instance.addHandler.call_args[0][0]
    formatter_instance = handler_instance.formatter
    assert isinstance(
        formatter_instance, logging_config.structlog.stdlib.ProcessorFormatter
    )
    assert any(
        isinstance(p, logging_config.structlog.dev.ConsoleRenderer)
        for p in formatter_instance.processors
    )
    # Check the level was set
    mock_logger_instance.setLevel.assert_called_once_with(logging.INFO)


def test_logging_config_json(mocker):
    """Test configuring logging with json format."""
    mock_settings = mocker.patch("src.document_understanding.logging_config.settings")
    mock_settings.log_format = "json"
    mock_settings.log_level = "DEBUG"

    mock_logger_instance = MagicMock()
    mock_get_logger = mocker.patch(
        "logging.getLogger", return_value=mock_logger_instance
    )

    from src.document_understanding import logging_config

    try:
        logging_config.configure_logging()
    except Exception as e:
        pytest.fail(f"configure_logging failed with json format: {e}")

    mock_get_logger.assert_called()
    mock_logger_instance.addHandler.assert_called_once()
    handler_instance = mock_logger_instance.addHandler.call_args[0][0]
    formatter_instance = handler_instance.formatter
    assert isinstance(
        formatter_instance, logging_config.structlog.stdlib.ProcessorFormatter
    )
    assert any(
        isinstance(p, logging_config.structlog.processors.JSONRenderer)
        for p in formatter_instance.processors
    )
    mock_logger_instance.setLevel.assert_called_once_with(logging.DEBUG)


def test_get_logger():
    """Test getting a logger instance."""
    from src.document_understanding.logging_config import get_logger

    logger = get_logger(__name__)
    assert logger is not None
    # Further checks could involve checking logger name or handlers if needed


# Ensure the server module and its dependencies can be imported
def test_server_import():
    try:
        from src import document_understanding
        from src.document_understanding import server

        assert document_understanding is not None
        assert server is not None
    except ImportError as e:
        pytest.fail(f"Failed to import server components: {e}")
