# src/document_understanding/logging_config.py
import logging
import sys
import structlog
import os
from typing import Any, Callable, List, Mapping, cast
from .settings import settings


def configure_logging():
    """Configures logging based on settings."""
    getattr(logging, settings.log_level.upper(), logging.WARNING)

    # Define the processor type for mypy
    ProcessorType = Callable[[Any, str, Mapping[str, Any]], Mapping[str, Any]]

    # Cast the processors to the correct type for mypy
    shared_processors: List[ProcessorType] = [
        cast(ProcessorType, structlog.stdlib.add_logger_name),
        cast(ProcessorType, structlog.stdlib.add_log_level),
        cast(ProcessorType, structlog.stdlib.ProcessorFormatter.wrap_for_formatter),
    ]

    # Configure handlers based on settings.log_format
    handlers: List[logging.Handler] = []

    # File Handler (Conditional)
    file_handler_added = False
    if settings.log_file:
        try:
            os.path.dirname(settings.log_file)
            # Directory creation handled elsewhere
            file_handler = logging.FileHandler(settings.log_file, mode="a")
            file_formatter = structlog.stdlib.ProcessorFormatter(
                processor=structlog.processors.JSONRenderer(),
                foreign_pre_chain=shared_processors,
            )
            file_handler.setFormatter(file_formatter)
            file_level = getattr(logging, settings.log_file_level.upper(), logging.INFO)
            file_handler.setLevel(file_level)
            handlers.append(file_handler)
            file_handler_added = True  # Mark file handler as added
            print(
                f"INFO: File logging enabled: {settings.log_file} at level {settings.log_file_level}",
                file=sys.stderr,
            )
        except Exception as e:
            print(
                f"ERROR: Could not configure file logging to {settings.log_file}: {e}",
                file=sys.stderr,
            )

    # Console Handler (Only if File Handler wasn't added)
    if not file_handler_added:
        console_handler = logging.StreamHandler(sys.stderr)
        if settings.log_format.lower() == "json":
            formatter = structlog.stdlib.ProcessorFormatter(
                processor=structlog.processors.JSONRenderer(),
                foreign_pre_chain=shared_processors,
            )
        else:  # plain format
            formatter = structlog.stdlib.ProcessorFormatter(
                processor=structlog.dev.ConsoleRenderer(colors=True),
                foreign_pre_chain=shared_processors,
            )
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)

    # Configure root logger
    root_logger = logging.getLogger()
    # Clear existing handlers to avoid duplicates if re-configured
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    # Add configured handlers
    for handler in handlers:
        root_logger.addHandler(handler)
    # Set overall level from settings
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger.setLevel(level)

    # === DEBUGGING PRINT ===
    print(f"DEBUG: Root logger handlers: {root_logger.handlers}", file=sys.stderr)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            # structlog.stdlib.ExtraAdder(), # Removed - caused errors
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


# Helper to get a logger instance
def get_logger(name: str = "document_understanding") -> structlog.stdlib.BoundLogger:
    """Get a logger instance, inheriting structlog configuration."""
    # This ensures that even loggers obtained outside the main config flow
    # (e.g., in library code) get the structlog processors applied.
    logger = structlog.get_logger(name)
    # Cast to the correct return type for mypy
    return cast(structlog.stdlib.BoundLogger, logger)
