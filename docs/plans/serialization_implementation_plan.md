# Serialization Implementation Plan

This document outlines the specific code changes required to implement dual JSON/XML serialization support in the Document Understanding MCP Server.

## 1. Core Components

### 1.1 Serialization Manager

Create a new module `src/document_understanding/serialization.py`:

```python
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pydantic import BaseModel

class SerializationFormat(Enum):
    """Supported serialization formats."""
    JSON = "json"
    XML = "xml"

class SerializationManager:
    """Manages serialization of response models to different formats."""

    @staticmethod
    def serialize(
        response_model: BaseModel,
        format: SerializationFormat = SerializationFormat.JSON
    ) -> str:
        """Serialize a response model to the specified format."""
        if format == SerializationFormat.JSON:
            return SerializationManager._serialize_to_json(response_model)
        elif format == SerializationFormat.XML:
            return SerializationManager._serialize_to_xml(response_model)
        else:
            raise ValueError(f"Unsupported serialization format: {format}")

    @staticmethod
    def _serialize_to_json(response_model: BaseModel) -> str:
        """Convert a Pydantic model to JSON string."""
        # Use Pydantic's built-in JSON serialization
        return response_model.model_dump_json()

    @staticmethod
    def _serialize_to_xml(response_model: BaseModel) -> str:
        """Convert a Pydantic model to XML string."""
        # Get model as dict
        model_dict = response_model.model_dump()

        # Create root element
        root = ET.Element(response_model.__class__.__name__)

        # Add attributes and child elements
        SerializationManager._dict_to_xml(model_dict, root)

        # Create XML declaration and convert to string
        xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_content = ET.tostring(root, encoding='utf-8', method='xml').decode('utf-8')

        return xml_declaration + xml_content

    @staticmethod
    def _dict_to_xml(d: Dict[str, Any], parent_element: ET.Element) -> None:
        """Recursively convert a dict to XML elements."""
        for key, value in d.items():
            if value is None:
                # Create empty element for None values
                ET.SubElement(parent_element, key)
                continue

            if isinstance(value, dict):
                # Nested dict becomes a nested element
                child = ET.SubElement(parent_element, key)
                SerializationManager._dict_to_xml(value, child)
            elif isinstance(value, list):
                # List becomes multiple elements with the same tag
                SerializationManager._list_to_xml(value, key, parent_element)
            else:
                # Simple values become elements with text content
                child = ET.SubElement(parent_element, key)

                # Handle special types
                if isinstance(value, datetime):
                    child.text = value.isoformat() + "Z"
                else:
                    child.text = str(value)

    @staticmethod
    def _list_to_xml(items: List[Any], item_name: str, parent_element: ET.Element) -> None:
        """Convert a list to XML elements."""
        # Create a container element for the list
        container = ET.SubElement(parent_element, item_name)

        for i, item in enumerate(items):
            if isinstance(item, dict):
                # For dictionaries, use the item type name if available, otherwise use a generic item name
                item_type = item.get("__type__", "Item")
                if "__type__" in item:
                    del item["__type__"]
                child = ET.SubElement(container, item_type)
                SerializationManager._dict_to_xml(item, child)
            elif isinstance(item, BaseModel):
                # For Pydantic models, use the model class name
                child = ET.SubElement(container, item.__class__.__name__)
                SerializationManager._dict_to_xml(item.model_dump(), child)
            elif isinstance(item, list):
                # For nested lists, use a generic name and recurse
                SerializationManager._list_to_xml(item, f"Item{i}", container)
            else:
                # For simple values, create an element with the value as text
                child = ET.SubElement(container, "Item")

                # Handle special types
                if isinstance(item, datetime):
                    child.text = item.isoformat() + "Z"
                else:
                    child.text = str(item)
```

### 1.2 Model Extensions

Extend `models.py` to support XML serialization hints:

```python
# Add to models.py

class XMLSerializationConfig:
    """Configuration for XML serialization of a model."""

    def __init__(
        self,
        element_name: Optional[str] = None,
        list_item_name: Optional[str] = None,
        attributes: Optional[List[str]] = None,
        namespace: Optional[str] = None
    ):
        self.element_name = element_name
        self.list_item_name = list_item_name
        self.attributes = attributes or []
        self.namespace = namespace

# Example usage in a model:
class PageContent(BaseModel):
    page_number: int = Field(..., description="1-based page number")
    text: str = Field(..., description="Extracted text content")
    error: Optional[str] = None

    class Config:
        xml_config = XMLSerializationConfig(
            element_name="Page",
            attributes=["page_number"]
        )
```

## 2. Server Integration

### 2.1 Request Format Parameter

Update `server.py` to handle format selection:

```python
# Add to imports
from .serialization import SerializationFormat, SerializationManager

# Update the tool handler function
def handle_tool_call(request, tool_name):
    # Extract format preference from request
    format_str = request.query_params.get("format", "json").lower()
    try:
        format = SerializationFormat(format_str)
    except ValueError:
        format = SerializationFormat.JSON

    # Process the tool request
    response_model = process_tool(tool_name, request.json())

    # Serialize to the requested format
    serialized_response = SerializationManager.serialize(response_model, format)

    # Set appropriate content type
    content_type = "application/json" if format == SerializationFormat.JSON else "application/xml"

    return Response(content=serialized_response, media_type=content_type)
```

### 2.2 Content Negotiation

Add support for HTTP content negotiation:

```python
def determine_response_format(request):
    """Determine the response format based on request parameters and Accept header."""
    # Check for explicit format parameter
    if "format" in request.query_params:
        format_str = request.query_params.get("format", "json").lower()
        try:
            return SerializationFormat(format_str)
        except ValueError:
            pass

    # Check Accept header
    accept_header = request.headers.get("Accept", "")
    if "application/xml" in accept_header or "text/xml" in accept_header:
        return SerializationFormat.XML

    # Default to JSON
    return SerializationFormat.JSON
```

## 3. Special Type Handling

### 3.1 Binary Data

Add special handling for binary data (e.g., images):

```python
# Add to SerializationManager
@staticmethod
def _handle_binary_data(value: bytes, element: ET.Element) -> None:
    """Convert binary data to Base64 for XML."""
    import base64
    encoded = base64.b64encode(value).decode('ascii')
    element.text = encoded
    element.set("encoding", "base64")
```

### 3.2 Spatial Data

Add special handling for spatial data (points, rectangles):

```python
# Add to SerializationManager
@staticmethod
def _handle_spatial_data(value: Dict[str, float], element: ET.Element) -> None:
    """Handle spatial data like points and rectangles."""
    # For points
    if "x" in value and "y" in value and len(value) == 2:
        element.set("x", str(value["x"]))
        element.set("y", str(value["y"]))
    # For rectangles
    elif "x0" in value and "y0" in value and "x1" in value and "y1" in value:
        element.set("x0", str(value["x0"]))
        element.set("y0", str(value["y0"]))
        element.set("x1", str(value["x1"]))
        element.set("y1", str(value["y1"]))
    else:
        # Fall back to standard dict handling
        SerializationManager._dict_to_xml(value, element)
```

## 4. Configuration

### 4.1 Server Configuration

Add configuration options for default serialization format:

```python
# Add to config.py or settings.py
DEFAULT_SERIALIZATION_FORMAT = SerializationFormat.JSON
```

### 4.2 Tool-Specific Configuration

Allow tool-specific serialization settings:

```python
# Add to tool registration
def register_tool(
    name,
    description,
    guidance=None,
    default_format=None,
    # ... other parameters
):
    # ... existing code
    tool_config["default_format"] = default_format or DEFAULT_SERIALIZATION_FORMAT
    # ... existing code
```

## 5. Testing

### 5.1 Unit Testing Strategy

#### 5.1.1 Serialization Manager Tests

```python
# tests/unit/test_serialization.py

import pytest
from datetime import datetime
from src.document_understanding.serialization import SerializationManager, SerializationFormat
from src.document_understanding.models import (
    MetadataResponse,
    MetadataResponseData,
    TextContentResponse,
    TextContentResponseData,
    PageContent,
    # Other model imports
)

class TestSerializationManager:
    """Test the SerializationManager class."""

    def test_json_serialization_basic(self):
        """Test basic JSON serialization."""
        # Create a simple response
        response = MetadataResponse(
            status="success",
            message="Test message",
            data=MetadataResponseData(
                page_count=10,
                metadata={"title": "Test Document"},
                has_embedded_images=True,
                has_vector_drawings=False
            )
        )

        # Serialize to JSON
        json_str = SerializationManager.serialize(response, SerializationFormat.JSON)

        # Parse the JSON and verify structure
        import json
        parsed = json.loads(json_str)
        assert parsed["status"] == "success"
        assert parsed["message"] == "Test message"
        assert parsed["data"]["page_count"] == 10
        assert parsed["data"]["metadata"]["title"] == "Test Document"
        assert parsed["data"]["has_embedded_images"] is True

    def test_xml_serialization_basic(self):
        """Test basic XML serialization."""
        # Create a simple response
        response = MetadataResponse(
            status="success",
            message="Test message",
            data=MetadataResponseData(
                page_count=10,
                metadata={"title": "Test Document"},
                has_embedded_images=True,
                has_vector_drawings=False
            )
        )

        # Serialize to XML
        xml_str = SerializationManager.serialize(response, SerializationFormat.XML)

        # Parse the XML and verify structure
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_str)
        assert root.tag == "MetadataResponse"
        assert root.find("status").text == "success"
        assert root.find("message").text == "Test message"
        assert int(root.find("data/page_count").text) == 10
        assert root.find("data/metadata/title").text == "Test Document"
        assert root.find("data/has_embedded_images").text.lower() == "true"
```

#### 5.1.2 Special Type Handling Tests

```python
def test_datetime_serialization(self):
    """Test serialization of datetime objects."""
    # Create a response with a fixed datetime
    fixed_time = datetime(2023, 6, 15, 14, 30, 45)
    response = MetadataResponse(
        status="success",
        timestamp=fixed_time,
        data=MetadataResponseData(
            page_count=10,
            metadata={}
        )
    )

    # Test JSON serialization
    json_str = SerializationManager.serialize(response, SerializationFormat.JSON)
    import json
    parsed_json = json.loads(json_str)
    assert parsed_json["timestamp"] == "2023-06-15T14:30:45Z"

    # Test XML serialization
    xml_str = SerializationManager.serialize(response, SerializationFormat.XML)
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_str)
    assert root.find("timestamp").text == "2023-06-15T14:30:45Z"

def test_spatial_data_serialization(self):
    """Test serialization of spatial data (points, rectangles)."""
    # Create a response with spatial data
    from src.document_understanding.models import Rect, Point

    response = LayoutResponse(
        status="success",
        data=LayoutResponseData(
            layout=[
                PageLayout(
                    page_number=1,
                    text_blocks=[
                        TextBlock(
                            number=1,
                            type=0,
                            bbox=Rect(x0=10.0, y0=20.0, x1=100.0, y1=50.0),
                            lines=[]
                        )
                    ],
                    images=[
                        SimpleImageInfo(
                            xref=1,
                            width=300,
                            height=200,
                            bbox=Rect(x0=200.0, y0=300.0, x1=500.0, y1=500.0)
                        )
                    ]
                )
            ],
            include_images=True,
            include_drawings=False
        )
    )

    # Test both formats
    json_str = SerializationManager.serialize(response, SerializationFormat.JSON)
    xml_str = SerializationManager.serialize(response, SerializationFormat.XML)

    # Verify JSON
    import json
    parsed_json = json.loads(json_str)
    assert parsed_json["data"]["layout"][0]["text_blocks"][0]["bbox"]["x0"] == 10.0

    # Verify XML
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_str)
    bbox = root.find(".//text_blocks/TextBlock/bbox")
    assert float(bbox.find("x0").text) == 10.0
```

#### 5.1.3 Complex Structure Tests

```python
def test_nested_list_serialization(self):
    """Test serialization of nested lists."""
    # Create a response with nested lists
    response = TableExtractionResponse(
        status="success",
        data=TableExtractionResponseData(
            tables=[
                Table(
                    page_number=1,
                    table_number=1,
                    data=[
                        ["Header1", "Header2", "Header3"],
                        ["Row1Col1", "Row1Col2", "Row1Col3"],
                        ["Row2Col1", "Row2Col2", "Row2Col3"]
                    ]
                )
            ]
        )
    )

    # Test JSON serialization
    json_str = SerializationManager.serialize(response, SerializationFormat.JSON)
    import json
    parsed_json = json.loads(json_str)
    assert parsed_json["data"]["tables"][0]["data"][0][0] == "Header1"
    assert parsed_json["data"]["tables"][0]["data"][1][1] == "Row1Col2"

    # Test XML serialization
    xml_str = SerializationManager.serialize(response, SerializationFormat.XML)
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_str)

    # Navigate to table data (exact path depends on implementation)
    table_data = root.findall(".//tables/Table/data/Item")
    assert len(table_data) > 0

    # Verify we can access the cell data
    row_data = table_data[0].findall("Item")
    assert row_data[0].text == "Header1"
```

#### 5.1.4 Edge Case Tests

```python
def test_empty_lists(self):
    """Test serialization of empty lists."""
    response = TableExtractionResponse(
        status="success",
        data=TableExtractionResponseData(
            tables=[]  # Empty list
        )
    )

    # Test both formats
    json_str = SerializationManager.serialize(response, SerializationFormat.JSON)
    xml_str = SerializationManager.serialize(response, SerializationFormat.XML)

    # Verify JSON
    import json
    parsed_json = json.loads(json_str)
    assert parsed_json["data"]["tables"] == []

    # Verify XML
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_str)
    tables_element = root.find(".//tables")
    assert tables_element is not None
    assert len(list(tables_element)) == 0

def test_none_values(self):
    """Test serialization of None values."""
    response = MetadataResponse(
        status="success",
        message=None,  # None value
        data=MetadataResponseData(
            page_count=10,
            metadata={"author": None},  # None in nested dict
            has_embedded_images=None  # None for boolean field
        )
    )

    # Test both formats
    json_str = SerializationManager.serialize(response, SerializationFormat.JSON)
    xml_str = SerializationManager.serialize(response, SerializationFormat.XML)

    # Verify JSON
    import json
    parsed_json = json.loads(json_str)
    assert parsed_json["message"] is None
    assert parsed_json["data"]["metadata"]["author"] is None
    assert parsed_json["data"]["has_embedded_images"] is None

    # Verify XML
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_str)
    # Check how None values are represented in XML (empty elements or missing)
    message_element = root.find("message")
    assert message_element is not None and message_element.text is None
```

### 5.2 Integration Testing

#### 5.2.1 API Endpoint Tests

```python
# tests/integration/test_api_serialization.py

import pytest
from starlette.testclient import TestClient
from src.document_understanding.server import app

client = TestClient(app)

class TestAPIFormatSelection:
    """Test API format selection."""

    def test_json_format_parameter(self):
        """Test JSON format selection via parameter."""
        response = client.get("/tools/extract_pdf_metadata?format=json&pdf_path=test.pdf")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert "status" in data

    def test_xml_format_parameter(self):
        """Test XML format selection via parameter."""
        response = client.get("/tools/extract_pdf_metadata?format=xml&pdf_path=test.pdf")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/xml"
        assert response.text.startswith("<?xml")

    def test_accept_header_json(self):
        """Test JSON format selection via Accept header."""
        response = client.get(
            "/tools/extract_pdf_metadata?pdf_path=test.pdf",
            headers={"Accept": "application/json"}
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_accept_header_xml(self):
        """Test XML format selection via Accept header."""
        response = client.get(
            "/tools/extract_pdf_metadata?pdf_path=test.pdf",
            headers={"Accept": "application/xml"}
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/xml"
```

#### 5.2.2 Tool-Specific Tests

```python
class TestToolsWithFormats:
    """Test all tools with both formats."""

    @pytest.mark.parametrize("format", ["json", "xml"])
    def test_extract_metadata(self, format):
        """Test extract_pdf_metadata with both formats."""
        response = client.get(f"/tools/extract_pdf_metadata?format={format}&pdf_path=test.pdf")
        assert response.status_code == 200

        # Verify content type
        expected_content_type = f"application/{format}"
        assert response.headers["content-type"] == expected_content_type

        # Basic validation of response structure
        if format == "json":
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            assert "page_count" in data["data"]
        else:  # xml
            assert response.text.startswith("<?xml")
            # Basic XML validation
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.text)
            assert root.tag == "MetadataResponse"
            assert root.find("status").text == "success"
            assert root.find("data/page_count") is not None

    # Similar tests for other tools
    @pytest.mark.parametrize("format", ["json", "xml"])
    def test_extract_text(self, format):
        """Test extract_pdf_contents with both formats."""
        # Implementation similar to above
        pass

    @pytest.mark.parametrize("format", ["json", "xml"])
    def test_extract_layout(self, format):
        """Test extract_pdf_layout with both formats."""
        # Implementation similar to above
        pass
```

#### 5.2.3 Error Handling Tests

```python
class TestErrorResponses:
    """Test error responses in both formats."""

    @pytest.mark.parametrize("format", ["json", "xml"])
    def test_missing_pdf(self, format):
        """Test error response for missing PDF."""
        response = client.get(f"/tools/extract_pdf_metadata?format={format}&pdf_path=nonexistent.pdf")
        assert response.status_code == 400  # or whatever is appropriate

        # Verify error structure
        if format == "json":
            data = response.json()
            assert data["status"] == "error"
            assert "error_code" in data
        else:  # xml
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.text)
            assert root.find("status").text == "error"
            assert root.find("error_code") is not None
```

### 5.3 Schema Validation Tests

```python
# tests/unit/test_schema_validation.py

import pytest
import json
import xmlschema
from src.document_understanding.serialization import SerializationManager, SerializationFormat
from src.document_understanding.models import (
    MetadataResponse,
    MetadataResponseData,
    # Other model imports
)

class TestSchemaValidation:
    """Test schema validation for both formats."""

    def test_json_schema_validation(self):
        """Test JSON responses against JSON Schema."""
        # Create a sample response
        response = MetadataResponse(
            status="success",
            data=MetadataResponseData(
                page_count=10,
                metadata={"title": "Test Document"}
            )
        )

        # Serialize to JSON
        json_str = SerializationManager.serialize(response, SerializationFormat.JSON)

        # Validate against JSON Schema
        import jsonschema
        schema_path = "schemas/json/metadata_response.json"
        with open(schema_path) as f:
            schema = json.load(f)

        parsed_json = json.loads(json_str)
        jsonschema.validate(parsed_json, schema)

    def test_xml_schema_validation(self):
        """Test XML responses against XML Schema."""
        # Create a sample response
        response = MetadataResponse(
            status="success",
            data=MetadataResponseData(
                page_count=10,
                metadata={"title": "Test Document"}
            )
        )

        # Serialize to XML
        xml_str = SerializationManager.serialize(response, SerializationFormat.XML)

        # Validate against XML Schema
        schema_path = "schemas/xml/metadata_response.xsd"
        schema = xmlschema.XMLSchema(schema_path)
        schema.validate(xml_str)
```

### 5.4 Performance Tests

```python
# tests/performance/test_serialization_performance.py

import pytest
import time
import statistics
from src.document_understanding.serialization import SerializationManager, SerializationFormat
from src.document_understanding.models import (
    TextContentResponse,
    TextContentResponseData,
    PageContent
)

class TestSerializationPerformance:
    """Test serialization performance."""

    def create_large_response(self, num_pages=100, text_length=1000):
        """Create a large response for performance testing."""
        pages = []
        for i in range(num_pages):
            pages.append(PageContent(
                page_number=i+1,
                text="X" * text_length
            ))

        return TextContentResponse(
            status="success",
            data=TextContentResponseData(
                pages=pages
            )
        )

    def test_serialization_speed(self):
        """Test serialization speed for both formats."""
        # Create responses of different sizes
        small_response = self.create_large_response(num_pages=10, text_length=100)
        medium_response = self.create_large_response(num_pages=50, text_length=500)
        large_response = self.create_large_response(num_pages=100, text_length=1000)

        responses = [small_response, medium_response, large_response]
        formats = [SerializationFormat.JSON, SerializationFormat.XML]

        results = {}

        for response in responses:
            num_pages = len(response.data.pages)
            for format in formats:
                # Run multiple times to get average
                times = []
                for _ in range(10):
                    start_time = time.time()
                    SerializationManager.serialize(response, format)
                    end_time = time.time()
                    times.append(end_time - start_time)

                avg_time = statistics.mean(times)
                results[f"{format.value}_{num_pages}_pages"] = avg_time

        # Print or assert on results
        for key, value in results.items():
            print(f"{key}: {value:.6f} seconds")

        # Compare performance between formats
        assert results["json_100_pages"] < results["xml_100_pages"] * 2  # XML should be at most 2x slower

    def test_response_size(self):
        """Test response size for both formats."""
        # Create a response
        response = self.create_large_response(num_pages=50, text_length=500)

        # Get serialized size for both formats
        json_str = SerializationManager.serialize(response, SerializationFormat.JSON)
        xml_str = SerializationManager.serialize(response, SerializationFormat.XML)

        json_size = len(json_str.encode('utf-8'))
        xml_size = len(xml_str.encode('utf-8'))

        print(f"JSON size: {json_size} bytes")
        print(f"XML size: {xml_size} bytes")

        # XML is typically larger than JSON, but should be within reasonable limits
        assert xml_size < json_size * 2  # XML should be at most 2x larger
```

### 5.5 LLM Integration Tests

```python
# tests/integration/test_llm_integration.py

import pytest
import json
import xml.etree.ElementTree as ET
from src.document_understanding.serialization import SerializationManager, SerializationFormat
from src.document_understanding.models import (
    MetadataResponse,
    MetadataResponseData,
    TextContentResponse,
    TextContentResponseData,
    PageContent
)

class TestLLMIntegration:
    """Test LLM integration scenarios."""

    def test_json_parsing_example(self):
        """Test that the JSON parsing example works."""
        # Create a sample response
        response = MetadataResponse(
            status="success",
            message="Metadata extracted successfully",
            data=MetadataResponseData(
                page_count=42,
                metadata={
                    "author": "John Doe",
                    "title": "Sample Document"
                },
                has_embedded_images=True,
                has_vector_drawings=False
            )
        )

        # Serialize to JSON
        json_str = SerializationManager.serialize(response, SerializationFormat.JSON)

        # This is the example code we provide to LLMs
        # It should work correctly with our response format
        import json
        parsed = json.loads(json_str)
        status = parsed["status"]
        message = parsed["message"]
        data = parsed["data"]
        page_count = data["page_count"]
        metadata = data["metadata"]
        author = metadata.get("author")

        # Verify the parsed values
        assert status == "success"
        assert message == "Metadata extracted successfully"
        assert page_count == 42
        assert author == "John Doe"

    def test_xml_parsing_example(self):
        """Test that the XML parsing example works."""
        # Create a sample response
        response = MetadataResponse(
            status="success",
            message="Metadata extracted successfully",
            data=MetadataResponseData(
                page_count=42,
                metadata={
                    "author": "John Doe",
                    "title": "Sample Document"
                },
                has_embedded_images=True,
                has_vector_drawings=False
            )
        )

        # Serialize to XML
        xml_str = SerializationManager.serialize(response, SerializationFormat.XML)

        # This is the example code we provide to LLMs
        # It should work correctly with our response format
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_str)
        status = root.find("status").text
        message = root.find("message").text
        data = root.find("data")
        page_count = int(data.find("page_count").text)
        metadata = data.find("metadata")
        author = metadata.find("author").text

        # Verify the parsed values
        assert status == "success"
        assert message == "Metadata extracted successfully"
        assert page_count == 42
        assert author == "John Doe"
```

## 6. Documentation

### 6.1 API Documentation

Update API documentation to include format options:

```python
# Add to OpenAPI schema
format_parameter = {
    "name": "format",
    "in": "query",
    "description": "Response format (json or xml)",
    "schema": {
        "type": "string",
        "enum": ["json", "xml"],
        "default": "json"
    },
    "required": False
}

# Add to each endpoint
for path in openapi_schema["paths"].values():
    for method in path.values():
        if "parameters" not in method:
            method["parameters"] = []
        method["parameters"].append(format_parameter)
```

### 6.2 XML Schema Definitions

Create XML Schema Definition (XSD) files for validation:

```xml
<!-- schemas/base_response.xsd -->
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="BaseToolResponse">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="status" type="xs:string"/>
        <xs:element name="message" type="xs:string" minOccurs="0"/>
        <xs:element name="api_version" type="xs:string"/>
        <xs:element name="timestamp" type="xs:dateTime"/>
        <xs:element name="data" type="xs:anyType" minOccurs="0"/>
        <xs:element name="error_code" type="xs:string" minOccurs="0"/>
        <xs:element name="error_details" minOccurs="0">
          <xs:complexType>
            <xs:sequence>
              <xs:any minOccurs="0" maxOccurs="unbounded" processContents="lax"/>
            </xs:sequence>
          </xs:complexType>
        </xs:element>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
```

## 7. Implementation Timeline

### Phase 1 (Week 1-2)
- Create SerializationManager class
- Implement basic JSON/XML serialization
- Add format selection parameter
- Update server to handle format selection
- Write basic unit tests for serialization

### Phase 2 (Week 3-4)
- Implement special type handling
- Add content negotiation
- Create XML schemas
- Implement comprehensive unit tests:
  * Serialization Manager tests
  * Special type handling tests
  * Complex structure tests
  * Edge case tests
- Update documentation

### Phase 3 (Week 5-6)
- Implement tool-specific serialization settings
- Add performance optimizations
- Create examples for LLM integration
- Implement integration tests:
  * API endpoint tests
  * Tool-specific tests
  * Error handling tests
  * Schema validation tests
  * Performance tests
  * LLM integration tests
- Finalize documentation

## 8. Dependencies

- XML libraries: Standard library `xml.etree.ElementTree` should be sufficient
- Testing: Existing pytest framework
- Documentation: Update existing documentation system

## 9. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Performance degradation | Medium | Implement caching, benchmark and optimize |
| XML serialization errors | High | Comprehensive error handling and testing |
| Backward compatibility issues | High | Maintain JSON as default, thorough testing |
| Complex type handling | Medium | Create specialized handlers for each complex type |
| Large response handling | Medium | Implement streaming for large responses |

## 10. Success Criteria

- All existing tests pass with both formats
- New serialization tests pass
- Performance benchmarks show acceptable overhead
- Documentation is complete and accurate
- LLM integration examples work correctly
