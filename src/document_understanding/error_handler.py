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
        return str(response_data.model_dump_json())
    else:
        logger.error(
            f"Handler for tool '{tool_name}' returned unexpected data type for serialization: {type(response_data)}"
        )
        raise TypeError(
            f"Handler for tool '{tool_name}' returned non-Pydantic data type."
        )
