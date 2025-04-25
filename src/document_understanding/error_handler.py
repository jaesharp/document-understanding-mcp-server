"""
Error handling utilities for document understanding server.

This module provides structured error handling for tool execution.
"""

import sys
import traceback
from typing import Any, Dict, Callable, TypeVar, Union
from functools import wraps

from pydantic import ValidationError
from .logging_config import get_logger
from .models import ErrorResponse

logger = get_logger(__name__)

# Generic type for function return - can be any type or ErrorResponse
R = TypeVar("R")
ToolResult = Union[R, ErrorResponse]


def handle_tool_errors(
    tool_name: str, arguments: Dict[str, Any]
) -> Callable[[Callable[..., R]], Callable[..., ToolResult[R]]]:
    """
    Decorator to handle errors in tool execution with consistent logging and error reporting.

    Args:
        tool_name: The name of the tool being executed
        arguments: The arguments passed to the tool

    Returns:
        A decorator function that wraps the tool execution with error handling
    """

    def decorator(func: Callable[..., R]) -> Callable[..., ToolResult[R]]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> ToolResult[R]:
            try:
                return func(*args, **kwargs)
            except FileNotFoundError as e:
                logger.warning(f"File not found for tool '{tool_name}': {e}")
                return ErrorResponse(
                    status="error",
                    error_code="file_not_found",
                    message=str(e),
                    error_details={
                        "tool_name": tool_name,
                        "arguments": {
                            k: v for k, v in arguments.items() if k != "password"
                        },
                        "error_type": "FileNotFoundError",
                    },
                )
            except ValidationError as e:
                logger.warning(
                    f"Pydantic validation error handling tool '{tool_name}': {e}"
                )
                return ErrorResponse(
                    status="error",
                    error_code="validation_error",
                    message=f"Value error handling tool '{tool_name}': {e}",
                    error_details={
                        "tool_name": tool_name,
                        "arguments": {
                            k: v for k, v in arguments.items() if k != "password"
                        },
                        "validation_errors": e.errors(),
                    },
                )
            except ValueError as e:
                logger.warning(f"Value error handling tool '{tool_name}': {e}")
                return ErrorResponse(
                    status="error",
                    error_code="value_error",
                    message=str(e),
                    error_details={
                        "tool_name": tool_name,
                        "arguments": {
                            k: v for k, v in arguments.items() if k != "password"
                        },
                        "error_type": "ValueError",
                    },
                )
            except NotImplementedError as e:
                print(f"DEBUG: NotImplementedError caught: {str(e)}", file=sys.stderr)
                logger.error(
                    f"Tool '{tool_name}' not implemented yet: {e}", exc_info=False
                )
                return ErrorResponse(
                    status="error",
                    error_code="not_implemented",
                    message=f"Tool '{tool_name}' is not fully implemented yet: {e}",
                    error_details={
                        "tool_name": tool_name,
                        "arguments": {
                            k: v for k, v in arguments.items() if k != "password"
                        },
                        "error_type": "NotImplementedError",
                    },
                )
            except RuntimeError as e:
                # Check if this RuntimeError wraps a ValidationError
                if hasattr(e, "__cause__") and isinstance(e.__cause__, ValidationError):
                    print(
                        f"DEBUG: RuntimeError wrapping ValidationError: {e.__cause__}",
                        file=sys.stderr,
                    )
                    return ErrorResponse(
                        status="error",
                        error_code="validation_error",
                        message=f"Value error handling tool '{tool_name}': {e.__cause__}",
                        error_details={
                            "tool_name": tool_name,
                            "arguments": {
                                k: v for k, v in arguments.items() if k != "password"
                            },
                            "validation_errors": (
                                e.__cause__.errors()
                                if hasattr(e.__cause__, "errors")
                                else str(e.__cause__)
                            ),
                        },
                    )

                # Regular RuntimeError handling
                logger.error(
                    f"Runtime error handling tool '{tool_name}': {e}", exc_info=True
                )
                return ErrorResponse(
                    status="error",
                    error_code="runtime_error",
                    message=str(e),
                    error_details={
                        "tool_name": tool_name,
                        "arguments": {
                            k: v for k, v in arguments.items() if k != "password"
                        },
                        "error_type": "RuntimeError",
                    },
                )
            except Exception as e:
                # Check if the exception is wrapping a ValidationError
                if hasattr(e, "__cause__") and isinstance(e.__cause__, ValidationError):
                    print(
                        f"DEBUG: Caught exception with ValidationError __cause__: {type(e)} -> {type(e.__cause__)}",
                        file=sys.stderr,
                    )
                    logger.warning(
                        f"Pydantic validation error wrapped in exception handling tool '{tool_name}': {e.__cause__}"
                    )
                    return ErrorResponse(
                        status="error",
                        error_code="validation_error",
                        message=f"Value error handling tool '{tool_name}': {e.__cause__}",
                        error_details={
                            "tool_name": tool_name,
                            "arguments": {
                                k: v for k, v in arguments.items() if k != "password"
                            },
                            "validation_errors": (
                                e.__cause__.errors()
                                if hasattr(e.__cause__, "errors")
                                else str(e.__cause__)
                            ),
                        },
                    )

                exc_traceback = traceback.format_exc()
                logger.error(
                    f"Unexpected error handling tool '{tool_name}': {e}\nTraceback:\n{exc_traceback}",
                    exc_info=False,
                    error=str(e),
                    tool_name=tool_name,
                    tool_arguments=arguments,
                )
                print(
                    f"ERROR [handle_call_tool]: Unexpected error handling tool '{tool_name}': {e}\n"
                    f"Traceback:\n{exc_traceback}",
                    file=sys.stderr,
                )
                return ErrorResponse(
                    status="error",
                    error_code="server_error",
                    message=f"An unexpected server error occurred while handling tool '{tool_name}'",
                    error_details={
                        "tool_name": tool_name,
                        "arguments": {
                            k: v for k, v in arguments.items() if k != "password"
                        },
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    },
                )

        return wrapper

    return decorator


def serialize_response_data(tool_name: str, response_data: Any) -> str:
    """
    Serializes the response data from a tool handler into a JSON string.
    Assumes response_data is a Pydantic model.

    Args:
        tool_name: The name of the tool
        response_data: The response data to serialize

    Returns:
        The serialized response as a JSON string

    Raises:
        TypeError: If the response data is not a recognized serializable type (Pydantic model).
    """
    if hasattr(response_data, "model_dump_json"):
        # Custom JSON encoder for PyMuPDF objects
        def pymupdf_json_encoder(obj):
            # Handle PyMuPDF Point objects
            if hasattr(obj, "x") and hasattr(obj, "y"):
                return {"x": float(obj.x), "y": float(obj.y)}
            # Handle PyMuPDF Rect objects
            elif (
                hasattr(obj, "x0")
                and hasattr(obj, "y0")
                and hasattr(obj, "x1")
                and hasattr(obj, "y1")
            ):
                return {
                    "x0": float(obj.x0),
                    "y0": float(obj.y0),
                    "x1": float(obj.x1),
                    "y1": float(obj.y1),
                }
            # Handle datetime objects
            elif hasattr(obj, "isoformat"):
                return obj.isoformat() + "Z"
            # Handle tuples and lists with PyMuPDF objects
            elif isinstance(obj, (list, tuple)):
                try:
                    # Try to convert each item in the list/tuple
                    return [pymupdf_json_encoder(item) for item in obj]
                except TypeError:
                    # If that fails, let the default handler deal with it
                    pass
            # Handle dictionaries with PyMuPDF objects
            elif isinstance(obj, dict):
                try:
                    # Try to convert each value in the dictionary
                    return {k: pymupdf_json_encoder(v) for k, v in obj.items()}
                except TypeError:
                    # If that fails, let the default handler deal with it
                    pass
            # Default case
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        try:
            # Try using the model's built-in JSON serialization
            return str(response_data.model_dump_json())
        except TypeError as e:
            # If that fails due to non-serializable objects, try with our custom encoder
            if "is not JSON serializable" in str(e):
                logger.warning(
                    f"Using custom JSON encoder for tool '{tool_name}' due to: {e}"
                )
                try:
                    # Convert to dict and then use json.dumps with custom encoder
                    import json

                    return json.dumps(
                        response_data.model_dump(), default=pymupdf_json_encoder
                    )
                except Exception as json_err:
                    logger.error(
                        f"Custom JSON serialization failed for tool '{tool_name}': {json_err}"
                    )
                    raise
            else:
                raise
    else:
        logger.error(
            f"Handler for tool '{tool_name}' returned unexpected data type for serialization: {type(response_data)}"
        )
        raise TypeError(
            f"Handler for tool '{tool_name}' returned non-Pydantic data type."
        )
