# JSON and XML Serialization Plan for Document Understanding Tools

## Overview

This document outlines the plan to enhance the Document Understanding MCP Server to support both JSON and XML serialization formats for tool responses. This dual-format approach will provide flexibility for different LLM models and use cases, allowing clients to choose the format that works best for their specific needs.

## Current Implementation

The Document Understanding MCP Server currently uses a JSON-based serialization approach:

1. **Response Models**: Pydantic models define the structure of responses (in `models.py`)
2. **Serialization**: Pydantic's built-in JSON serialization converts models to JSON strings
3. **Response Format**: All tools return responses in a consistent JSON structure with:
   - Status (`success` or `error`)
   - Message (optional description)
   - API version and timestamp
   - Data (tool-specific response data)
   - Error details (when applicable)

## Benefits of Adding XML Support

1. **Enhanced LLM Parsing**: Some LLMs may process structured XML more effectively than JSON
2. **Hierarchical Data Representation**: XML's native hierarchical structure maps well to document elements
3. **Schema Validation**: XML schemas can provide stronger validation for complex document structures
4. **Namespace Support**: XML namespaces can help organize different aspects of document analysis
5. **Improved Readability**: XML can be more human-readable for complex nested structures
6. **Compatibility**: Some document processing systems may prefer XML for integration

## Implementation Strategy

### 1. Serialization Framework

Create a flexible serialization framework that supports both formats:

```python
class SerializationFormat(Enum):
    JSON = "json"
    XML = "xml"

class SerializationManager:
    @staticmethod
    def serialize(response_model, format: SerializationFormat = SerializationFormat.JSON):
        """Serialize a response model to the specified format."""
        if format == SerializationFormat.JSON:
            return SerializationManager._serialize_to_json(response_model)
        elif format == SerializationFormat.XML:
            return SerializationManager._serialize_to_xml(response_model)
        else:
            raise ValueError(f"Unsupported serialization format: {format}")

    @staticmethod
    def _serialize_to_json(response_model):
        """Convert a Pydantic model to JSON string."""
        return response_model.model_dump_json()

    @staticmethod
    def _serialize_to_xml(response_model):
        """Convert a Pydantic model to XML string."""
        # Implementation details below
```

### 2. XML Serialization Implementation

Implement XML serialization using a combination of:

1. **Model-to-XML Mapping**: Define how each Pydantic model maps to XML elements
2. **XML Generation Library**: Use a library like `lxml` or `dicttoxml` for conversion
3. **Custom Field Handling**: Implement special handling for complex types

Example implementation:

```python
def _serialize_to_xml(response_model):
    """Convert a Pydantic model to XML string."""
    # Get model as dict
    model_dict = response_model.model_dump()

    # Create root element
    root = ET.Element(response_model.__class__.__name__)

    # Add attributes and child elements
    _dict_to_xml(model_dict, root)

    # Convert to string
    return ET.tostring(root, encoding='utf-8', method='xml').decode('utf-8')

def _dict_to_xml(d, parent_element):
    """Recursively convert a dict to XML elements."""
    for key, value in d.items():
        if value is None:
            # Skip None values
            continue

        if isinstance(value, dict):
            # Nested dict becomes a nested element
            child = ET.SubElement(parent_element, key)
            _dict_to_xml(value, child)
        elif isinstance(value, list):
            # List becomes multiple elements with the same tag
            _list_to_xml(value, key, parent_element)
        else:
            # Simple values become attributes or text content
            if isinstance(value, (str, int, float, bool)):
                child = ET.SubElement(parent_element, key)
                child.text = str(value)
            else:
                # Handle special types (datetime, etc.)
                child = ET.SubElement(parent_element, key)
                child.text = str(value)
```

### 3. Response Format Selection

Add a mechanism to select the response format:

1. **Request Parameter**: Allow clients to specify the desired format in the request
2. **Configuration Setting**: Provide a server-level default format setting
3. **Tool-Specific Format**: Allow different formats for different tools if needed

```python
def handle_tool_request(request, tool_name):
    # Extract format preference from request
    format_str = request.query_params.get("format", "json").lower()
    format = SerializationFormat.JSON if format_str == "json" else SerializationFormat.XML

    # Process the tool request
    response_model = process_tool(tool_name, request.json())

    # Serialize to the requested format
    serialized_response = SerializationManager.serialize(response_model, format)

    # Set appropriate content type
    content_type = "application/json" if format == SerializationFormat.JSON else "application/xml"

    return Response(content=serialized_response, media_type=content_type)
```

### 4. XML Schema Definitions

Create XML Schema Definition (XSD) files for each response type:

1. **Base Response Schema**: Define the common structure for all responses
2. **Tool-Specific Schemas**: Define schemas for each tool's response format
3. **Documentation**: Include schema documentation for client developers

Example XSD for base response:

```xml
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

### 5. Special Handling for Complex Types

Implement special handling for complex data types:

1. **Binary Data**: Use Base64 encoding for image data in both formats
2. **Nested Structures**: Preserve hierarchy in XML representation
3. **Collections**: Handle lists and dictionaries appropriately
4. **Coordinates**: Represent spatial data (bounding boxes, points) consistently

## Implementation Phases

### Phase 1: Framework and Basic XML Support

1. Create the `SerializationManager` class
2. Implement basic XML serialization for simple response types
3. Add format selection parameter to the API
4. Write basic unit tests for serialization
5. Update documentation to reflect format options

### Phase 2: Complete XML Implementation

1. Implement XML serialization for all response types
2. Create XML schemas (XSD) for validation
3. Implement special type handling (datetime, spatial data, etc.)
4. Implement comprehensive unit tests:
   - Serialization Manager tests
   - Special type handling tests
   - Complex structure tests
   - Edge case tests
5. Update error handling for XML-specific issues

### Phase 3: Enhanced Features

1. Add content negotiation via HTTP Accept headers
2. Implement format-specific optimizations
3. Add support for XML namespaces
4. Create examples and documentation for both formats
5. Implement tool-specific serialization settings

### Phase 4: Integration and Testing

1. Implement comprehensive integration tests:
   - API endpoint tests
   - Tool-specific tests
   - Error handling tests
   - Schema validation tests
   - Performance tests
   - LLM integration tests
2. Benchmark performance of both serialization formats
3. Integrate with LLM models to test parsing capabilities
4. Make final adjustments based on testing results

## XML Format Examples

### Metadata Response

```xml
<MetadataResponse>
  <status>success</status>
  <message>Metadata extracted successfully</message>
  <api_version>1.0.0</api_version>
  <timestamp>2023-06-15T14:30:45Z</timestamp>
  <data>
    <page_count>42</page_count>
    <metadata>
      <author>John Doe</author>
      <title>Sample Document</title>
      <creation_date>2023-01-15T10:30:00Z</creation_date>
    </metadata>
    <has_embedded_images>true</has_embedded_images>
    <has_vector_drawings>false</has_vector_drawings>
  </data>
</MetadataResponse>
```

### Text Content Response

```xml
<TextContentResponse>
  <status>success</status>
  <message>Text content extracted successfully</message>
  <api_version>1.0.0</api_version>
  <timestamp>2023-06-15T14:32:10Z</timestamp>
  <data>
    <pages>
      <PageContent>
        <page_number>1</page_number>
        <text>This is the content of page 1...</text>
      </PageContent>
      <PageContent>
        <page_number>2</page_number>
        <text>This is the content of page 2...</text>
      </PageContent>
    </pages>
  </data>
</TextContentResponse>
```

### Layout Response

```xml
<LayoutResponse>
  <status>success</status>
  <message>Layout extracted successfully</message>
  <api_version>1.0.0</api_version>
  <timestamp>2023-06-15T14:33:20Z</timestamp>
  <data>
    <layout>
      <PageLayout>
        <page_number>1</page_number>
        <text_blocks>
          <TextBlock>
            <number>0</number>
            <type>1</type>
            <bbox>
              <x0>72.0</x0>
              <y0>72.0</y0>
              <x1>540.0</x1>
              <y1>108.0</y1>
            </bbox>
            <lines>
              <!-- Text lines data -->
            </lines>
          </TextBlock>
        </text_blocks>
        <images>
          <SimpleImageInfo>
            <xref>12</xref>
            <width>300</width>
            <height>200</height>
            <bbox>
              <x0>100.0</x0>
              <y0>200.0</y0>
              <x1>400.0</x1>
              <y1>400.0</y1>
            </bbox>
          </SimpleImageInfo>
        </images>
      </PageLayout>
    </layout>
    <include_images>true</include_images>
    <include_drawings>false</include_drawings>
  </data>
</LayoutResponse>
```

## Technical Considerations

### 1. Performance Impact

XML serialization may have different performance characteristics compared to JSON:

- **Serialization Speed**: XML generation might be slower than JSON
- **Response Size**: XML responses are typically larger than equivalent JSON
- **Parsing Overhead**: XML parsing in client applications may require more resources

Mitigation: Implement caching for frequently requested responses and benchmark both formats.

### 2. Error Handling

Enhance error handling for XML-specific issues:

- Invalid XML characters
- Namespace conflicts
- Schema validation failures
- Encoding issues

## Comprehensive Testing Strategy

A robust testing strategy is essential for ensuring both serialization formats work correctly and efficiently. Our testing approach includes:

### 1. Unit Testing

- **Serialization Manager Tests**: Verify basic serialization functionality for both formats
- **Special Type Handling Tests**: Ensure complex types like datetime, spatial data, and binary content are handled correctly
- **Complex Structure Tests**: Validate serialization of nested structures, lists, and dictionaries
- **Edge Case Tests**: Test empty collections, null values, and other edge cases

### 2. Integration Testing

- **API Endpoint Tests**: Verify format selection via parameters and Accept headers
- **Tool-Specific Tests**: Test each document understanding tool with both formats
- **Error Handling Tests**: Ensure errors are properly serialized in both formats

### 3. Schema Validation

- **JSON Schema Tests**: Validate JSON responses against JSON Schema definitions
- **XML Schema Tests**: Validate XML responses against XML Schema (XSD) definitions

### 4. Performance Testing

- **Serialization Speed**: Measure and compare serialization time for both formats
- **Response Size**: Compare the size of equivalent responses in both formats
- **Memory Usage**: Monitor memory usage during serialization

### 5. LLM Integration Testing

- **Parsing Examples**: Verify that the parsing examples we provide to LLMs work correctly
- **Format-Specific Prompts**: Test that our format-specific prompt templates produce expected results
- **Error Recovery**: Ensure LLMs can handle and recover from parsing errors

This comprehensive testing strategy ensures that both serialization formats are reliable, performant, and compatible with LLM models.

## LLM Integration Considerations

### 1. Format Selection Guidance

Provide guidance to LLMs on when to use each format:

- **JSON**: Better for simple responses, smaller payloads, JavaScript clients
- **XML**: Better for complex hierarchical data, strong validation requirements

### 2. Parsing Examples

Include examples of parsing both formats in LLM prompts:

```python
# JSON parsing example
import json
response = json.loads(response_text)
page_count = response["data"]["page_count"]

# XML parsing example
import xml.etree.ElementTree as ET
root = ET.fromstring(response_text)
page_count = int(root.find("./data/page_count").text)
```

### 3. Format-Specific Prompts

Develop format-specific prompt templates that help LLMs extract information effectively from each format.

## Conclusion

Supporting both JSON and XML serialization formats will enhance the flexibility and usability of the Document Understanding MCP Server. This dual-format approach allows clients to choose the format that best suits their needs while maintaining a consistent logical structure across both representations.

The implementation will be phased to ensure thorough testing and validation at each stage, with backward compatibility as a key requirement. The end result will be a more versatile API that can better integrate with a wide range of client applications and LLM models.
