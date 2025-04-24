import pytest
from unittest.mock import patch, MagicMock
import json

from src.document_understanding.error_handler import (
    handle_tool_errors,
    serialize_response_data,
)
from src.document_understanding.models import ErrorResponse, BaseToolResponse
from pydantic import ValidationError, BaseModel


class SampleModel(BaseModel):
    """Test model for serialization tests"""

    name: str
    value: int


def test_handle_tool_errors_file_not_found():
    """Test error handler handles FileNotFoundError correctly"""

    @handle_tool_errors("test_tool", {"arg1": "value1", "password": "secret"})
    def function_that_raises():
        raise FileNotFoundError("File not found message")

    result = function_that_raises()

    assert isinstance(result, ErrorResponse)
    assert result.status == "error"
    assert result.error_code == "file_not_found"
    assert "File not found message" in result.message
    assert result.error_details["tool_name"] == "test_tool"
    assert result.error_details["arguments"] == {"arg1": "value1"}  # password removed
    assert result.error_details["error_type"] == "FileNotFoundError"


def test_handle_tool_errors_value_error():
    """Test error handler handles ValueError correctly"""

    @handle_tool_errors("test_tool", {"arg1": "value1"})
    def function_that_raises():
        raise ValueError("Value error message")

    result = function_that_raises()

    assert isinstance(result, ErrorResponse)
    assert result.status == "error"
    assert result.error_code == "value_error"
    assert "Value error message" in result.message
    assert result.error_details["tool_name"] == "test_tool"
    assert result.error_details["error_type"] == "ValueError"


def test_handle_tool_errors_validation_error():
    """Test error handler handles Pydantic ValidationError correctly"""

    @handle_tool_errors("test_tool", {"arg1": "value1"})
    def function_that_raises():
        # Create a validation error by attempting to create a model with invalid data
        SampleModel(name=123, value="not an int")  # Types are wrong

    result = function_that_raises()

    assert isinstance(result, ErrorResponse)
    assert result.status == "error"
    assert result.error_code == "validation_error"
    assert "test_tool" in result.message
    assert result.error_details["tool_name"] == "test_tool"
    assert "validation_errors" in result.error_details


def test_handle_tool_errors_runtime_error():
    """Test error handler handles RuntimeError correctly"""

    @handle_tool_errors("test_tool", {"arg1": "value1"})
    def function_that_raises():
        raise RuntimeError("Runtime error message")

    result = function_that_raises()

    assert isinstance(result, ErrorResponse)
    assert result.status == "error"
    assert result.error_code == "runtime_error"
    assert "Runtime error message" in result.message
    assert result.error_details["tool_name"] == "test_tool"
    assert result.error_details["error_type"] == "RuntimeError"


def test_handle_tool_errors_not_implemented():
    """Test error handler handles NotImplementedError correctly"""

    @handle_tool_errors("test_tool", {"arg1": "value1"})
    def function_that_raises():
        raise NotImplementedError("Not implemented message")

    result = function_that_raises()

    assert isinstance(result, ErrorResponse)
    assert result.status == "error"
    assert result.error_code == "not_implemented"
    assert "Not implemented message" in result.message
    assert result.error_details["tool_name"] == "test_tool"
    assert result.error_details["error_type"] == "NotImplementedError"


def test_handle_tool_errors_generic_exception():
    """Test error handler handles generic Exception correctly"""

    @handle_tool_errors("test_tool", {"arg1": "value1"})
    def function_that_raises():
        raise Exception("Generic exception message")

    result = function_that_raises()

    assert isinstance(result, ErrorResponse)
    assert result.status == "error"
    assert result.error_code == "server_error"
    assert "unexpected server error" in result.message.lower()
    assert result.error_details["tool_name"] == "test_tool"
    assert result.error_details["error_type"] == "Exception"
    assert result.error_details["error_message"] == "Generic exception message"


def test_handle_tool_errors_nested_validation_error():
    """Test error handler handles Exception with nested ValidationError correctly"""

    @handle_tool_errors("test_tool", {"arg1": "value1"})
    def function_that_raises():
        try:
            # Create a validation error
            SampleModel(name=123, value="not an int")
        except ValidationError as ve:
            # Wrap it in another exception
            raise RuntimeError("Wrapped validation error") from ve

    result = function_that_raises()

    assert isinstance(result, ErrorResponse)
    assert result.status == "error"
    assert result.error_code == "validation_error"
    assert "test_tool" in result.message
    assert result.error_details["tool_name"] == "test_tool"
    assert "validation_errors" in result.error_details


def test_serialize_response_data():
    """Test serialization of response data"""
    test_model = SampleModel(name="test", value=123)

    result = serialize_response_data("test_tool", test_model)

    # Should be a valid JSON string
    parsed = json.loads(result)
    assert parsed["name"] == "test"
    assert parsed["value"] == 123


def test_serialize_response_data_type_error():
    """Test serialization raises TypeError for invalid types"""

    with pytest.raises(TypeError) as excinfo:
        serialize_response_data("test_tool", "not a pydantic model")

    assert "returned non-Pydantic data type" in str(excinfo.value)
