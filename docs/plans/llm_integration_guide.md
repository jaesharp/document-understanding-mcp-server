# LLM Integration Guide for JSON/XML Serialization

This guide provides recommendations for integrating Large Language Models (LLMs) with the Document Understanding MCP Server's dual JSON/XML serialization capabilities.

## Format Selection Guidance

### When to Use JSON

JSON format is recommended when:

1. **Simple Data Structure**: The response has a relatively flat structure
2. **Smaller Payload Size**: Minimizing response size is important
3. **JavaScript Clients**: The client is a JavaScript application
4. **Familiarity**: The LLM is more familiar with JSON parsing
5. **Performance**: Response time is critical

Example JSON response:

```json
{
  "status": "success",
  "message": "Metadata extracted successfully",
  "api_version": "1.0.0",
  "timestamp": "2023-06-15T14:30:45Z",
  "data": {
    "page_count": 42,
    "metadata": {
      "author": "John Doe",
      "title": "Sample Document"
    },
    "has_embedded_images": true,
    "has_vector_drawings": false
  }
}
```

### When to Use XML

XML format is recommended when:

1. **Complex Hierarchical Data**: The response has deeply nested structures
2. **Strong Validation Requirements**: Schema validation is important
3. **Semantic Clarity**: Element names provide clearer context than JSON keys
4. **Mixed Content**: The response contains mixed text and structured data
5. **Integration with XML-based Systems**: The client expects XML format

Example XML response:

```xml
<?xml version="1.0" encoding="UTF-8"?>
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
    </metadata>
    <has_embedded_images>true</has_embedded_images>
    <has_vector_drawings>false</has_vector_drawings>
  </data>
</MetadataResponse>
```

## LLM Parsing Examples

### JSON Parsing Examples

Provide these examples to help LLMs parse JSON responses:

#### Python

```python
import json

# Parse the JSON response
response = json.loads(response_text)

# Access basic response fields
status = response["status"]
message = response["message"]
api_version = response["api_version"]

# Access data fields
data = response["data"]
page_count = data["page_count"]
metadata = data["metadata"]
author = metadata.get("author")

# Access list items (e.g., pages in text content response)
if "pages" in data:
    for page in data["pages"]:
        page_number = page["page_number"]
        text = page["text"]
        print(f"Page {page_number}: {text[:50]}...")
```

#### JavaScript

```javascript
// Parse the JSON response
const response = JSON.parse(responseText);

// Access basic response fields
const status = response.status;
const message = response.message;
const apiVersion = response.api_version;

// Access data fields
const data = response.data;
const pageCount = data.page_count;
const metadata = data.metadata;
const author = metadata.author;

// Access list items (e.g., pages in text content response)
if (data.pages) {
    data.pages.forEach(page => {
        const pageNumber = page.page_number;
        const text = page.text;
        console.log(`Page ${pageNumber}: ${text.substring(0, 50)}...`);
    });
}
```

### XML Parsing Examples

Provide these examples to help LLMs parse XML responses:

#### Python

```python
import xml.etree.ElementTree as ET

# Parse the XML response
root = ET.fromstring(response_text)

# Access basic response fields
status = root.find("status").text
message = root.find("message").text if root.find("message") is not None else None
api_version = root.find("api_version").text

# Access data fields
data = root.find("data")
page_count = int(data.find("page_count").text)
metadata = data.find("metadata")
author = metadata.find("author").text if metadata.find("author") is not None else None

# Access list items (e.g., pages in text content response)
pages = data.find("pages")
if pages is not None:
    for page in pages.findall("PageContent"):
        page_number = int(page.find("page_number").text)
        text = page.find("text").text
        print(f"Page {page_number}: {text[:50]}...")
```

#### JavaScript

```javascript
// Parse the XML response
const parser = new DOMParser();
const xmlDoc = parser.parseFromString(responseText, "text/xml");

// Access basic response fields
const status = xmlDoc.querySelector("status").textContent;
const messageElement = xmlDoc.querySelector("message");
const message = messageElement ? messageElement.textContent : null;
const apiVersion = xmlDoc.querySelector("api_version").textContent;

// Access data fields
const data = xmlDoc.querySelector("data");
const pageCount = parseInt(data.querySelector("page_count").textContent);
const metadata = data.querySelector("metadata");
const authorElement = metadata.querySelector("author");
const author = authorElement ? authorElement.textContent : null;

// Access list items (e.g., pages in text content response)
const pages = data.querySelector("pages");
if (pages) {
    const pageElements = pages.querySelectorAll("PageContent");
    pageElements.forEach(page => {
        const pageNumber = parseInt(page.querySelector("page_number").textContent);
        const text = page.querySelector("text").textContent;
        console.log(`Page ${pageNumber}: ${text.substring(0, 50)}...`);
    });
}
```

## Format-Specific Prompts

### JSON-Specific Prompts

When working with JSON responses, use these prompt templates:

#### Metadata Extraction

```
Extract the following information from the JSON response:
1. Document title
2. Author
3. Page count
4. Whether the document contains images

JSON Response:
{response_json}
```

#### Text Content Analysis

```
Analyze the text content from the JSON response and provide a summary of each page.

JSON Response:
{response_json}
```

#### Layout Analysis

```
Extract the following layout information from the JSON response:
1. Number of text blocks on page 1
2. Positions of images on page 1
3. Bounding boxes of the first 3 text blocks

JSON Response:
{response_json}
```

### XML-Specific Prompts

When working with XML responses, use these prompt templates:

#### Metadata Extraction

```
Extract the following information from the XML response:
1. Document title
2. Author
3. Page count
4. Whether the document contains images

XML Response:
{response_xml}
```

#### Text Content Analysis

```
Analyze the text content from the XML response and provide a summary of each page.

XML Response:
{response_xml}
```

#### Layout Analysis

```
Extract the following layout information from the XML response:
1. Number of text blocks on page 1
2. Positions of images on page 1
3. Bounding boxes of the first 3 text blocks

XML Response:
{response_xml}
```

## Error Handling

### JSON Error Handling

```python
import json

try:
    response = json.loads(response_text)
    
    # Check for error status
    if response["status"] == "error":
        error_code = response["error_code"]
        error_message = response["message"]
        error_details = response.get("error_details", {})
        
        print(f"Error {error_code}: {error_message}")
        if error_details:
            print(f"Details: {error_details}")
    else:
        # Process successful response
        data = response["data"]
        # ...
except json.JSONDecodeError:
    print("Invalid JSON response")
except KeyError as e:
    print(f"Missing expected field in response: {e}")
```

### XML Error Handling

```python
import xml.etree.ElementTree as ET

try:
    root = ET.fromstring(response_text)
    
    # Check for error status
    status_element = root.find("status")
    if status_element is not None and status_element.text == "error":
        error_code_element = root.find("error_code")
        error_code = error_code_element.text if error_code_element is not None else "unknown"
        
        message_element = root.find("message")
        error_message = message_element.text if message_element is not None else "Unknown error"
        
        print(f"Error {error_code}: {error_message}")
        
        # Process error details if available
        error_details = root.find("error_details")
        if error_details is not None:
            for detail in error_details:
                print(f"  {detail.tag}: {detail.text}")
    else:
        # Process successful response
        data = root.find("data")
        # ...
except ET.ParseError:
    print("Invalid XML response")
except AttributeError as e:
    print(f"Missing expected element in response: {e}")
```

## Performance Considerations

When working with large responses, consider these performance tips:

### JSON Performance Tips

1. **Streaming Parsing**: For large responses, use streaming JSON parsers
2. **Selective Extraction**: Extract only the needed fields rather than parsing the entire response
3. **Pagination**: Request paginated results for large collections

Example of streaming JSON parsing:

```python
import ijson  # Incremental JSON parser

with open('large_response.json', 'rb') as f:
    # Extract only specific fields
    for prefix, event, value in ijson.parse(f):
        if prefix == 'data.pages.item.page_number':
            page_number = value
        elif prefix == 'data.pages.item.text':
            # Process text for the current page
            process_page_text(page_number, value)
```

### XML Performance Tips

1. **Iterative Parsing**: Use iterative parsing for large XML documents
2. **XPath Queries**: Use XPath to directly access needed elements
3. **Selective Processing**: Process only relevant branches of the XML tree

Example of iterative XML parsing:

```python
import xml.etree.ElementTree as ET

# Iterative parsing for large XML
context = ET.iterparse('large_response.xml', events=('start', 'end'))
for event, elem in context:
    if event == 'end' and elem.tag == 'PageContent':
        page_number = int(elem.find('page_number').text)
        text = elem.find('text').text
        
        # Process the page
        process_page_text(page_number, text)
        
        # Clear element to free memory
        elem.clear()
```

## Best Practices

1. **Format Detection**: Always check the content type or response format before parsing
2. **Graceful Degradation**: Handle both formats if possible, with a preference for one
3. **Error Handling**: Implement robust error handling for parsing issues
4. **Validation**: Validate responses against expected schemas
5. **Documentation**: Document the format used in your analysis

Example of format detection:

```python
def parse_response(response_text, content_type=None):
    """Parse response based on content type or detected format."""
    # Try to detect format if content_type is not provided
    if content_type is None:
        if response_text.strip().startswith('<?xml') or response_text.strip().startswith('<'):
            content_type = 'application/xml'
        else:
            content_type = 'application/json'
    
    # Parse based on content type
    if 'xml' in content_type.lower():
        return parse_xml_response(response_text)
    else:
        return parse_json_response(response_text)
```

## Conclusion

By following these guidelines, LLMs can effectively work with both JSON and XML response formats from the Document Understanding MCP Server. The choice of format should be based on the specific requirements of the task, with consideration for data complexity, validation needs, and integration requirements.
