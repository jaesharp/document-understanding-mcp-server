# Multi-Document Type Support Plan

## Overview

This document outlines the planned evolution of the Document Understanding MCP Server to support multiple document types beyond PDF. The current architecture is tightly coupled to PDF-specific libraries and assumptions, and this plan proposes a more flexible, handle-based approach that can accommodate diverse document formats.

## Current Architecture Limitations

The current architecture has several PDF-specific assumptions:

1. **Naming**: Functions, variables, and paths contain "pdf" (e.g., `extract_pdf_contents`, `DOCUMENT_UNDERSTANDING_BASE_PATH`)
2. **File handling**: Direct file path references assume PDF files
3. **Extraction logic**: Tightly coupled to PyMuPDF and PDF-specific libraries
4. **Tool definitions**: Hardcoded for PDF operations

## Proposed Interface Evolution: Document Handle Approach

### 1. Document Registration and Handle Generation

```json
// LLM calls register-document
{
  "name": "register-document",
  "arguments": {
    "source": "file:///path/to/document.docx",
    // Alternative sources:
    // "source": "data://base64-encoded-content",
    // "source": "http://example.com/document.xlsx",
    "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document" // Optional, can be auto-detected
  }
}

// Server response
{
  "status": "success",
  "document_handle": "doc_8f72a1b5", // Session-specific token
  "detected_type": "docx",
  "page_count": 5,
  "size_bytes": 24560
}
```

### 2. Document Type Detection

```json
// LLM calls detect-document-type
{
  "name": "detect-document-type",
  "arguments": {
    "document_handle": "doc_8f72a1b5"
  }
}

// Server response
{
  "status": "success",
  "document_handle": "doc_8f72a1b5",
  "type": "docx",
  "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "confidence": 0.98,
  "available_extractors": ["text", "metadata", "tables", "images"]
}
```

### 3. Unified Content Extraction

```json
// LLM calls extract-content
{
  "name": "extract-content",
  "arguments": {
    "document_handle": "doc_8f72a1b5",
    "pages": "1-3",
    "format": "text", // Could be "markdown", "html", etc.
    "extraction_hints": {
      "include_tables": true,
      "preserve_layout": false
    }
  }
}
```

### 4. Document-Type Specific Operations

```json
// LLM calls extract-spreadsheet-data (for Excel/CSV files)
{
  "name": "extract-spreadsheet-data",
  "arguments": {
    "document_handle": "doc_8f72a1b5",
    "sheet": "Sheet1", // Or sheet index
    "range": "A1:D10", // Optional
    "include_formulas": false
  }
}
```

### 5. Document Release

```json
// LLM calls release-document
{
  "name": "release-document",
  "arguments": {
    "document_handle": "doc_8f72a1b5"
  }
}
```

## Implementation Considerations

### 1. Document Handler Service

Create a central `DocumentHandlerService` that:
- Manages document registration and handle generation
- Maintains a session-to-document mapping
- Handles document lifecycle (cleanup of temporary files)
- Routes extraction requests to appropriate extractors

```python
class DocumentHandlerService:
    def __init__(self):
        self.documents = {}  # Maps handles to document objects
        self.extractors = {}  # Maps document types to extractor classes
        
    def register_document(self, source, mime_type=None):
        # Download/copy/decode document from source
        # Detect document type if mime_type not provided
        # Create appropriate document object
        # Generate and return handle
        
    def get_document(self, handle):
        # Return document object for handle
        
    def release_document(self, handle):
        # Clean up resources for document
```

### 2. Document Type Abstraction

Create a base `Document` class with document-type specific implementations:

```python
class Document(ABC):
    @abstractmethod
    def get_content(self, pages=None, **options):
        pass
        
    @abstractmethod
    def get_metadata(self):
        pass
    
    @property
    @abstractmethod
    def page_count(self):
        pass

class PDFDocument(Document):
    def __init__(self, path):
        self.doc = fitz.open(path)
        
    def get_content(self, pages=None, **options):
        # Extract content using PyMuPDF
        
class DocxDocument(Document):
    def __init__(self, path):
        self.doc = docx.Document(path)
        
    def get_content(self, pages=None, **options):
        # Extract content using python-docx
```

### 3. Extractor Factory Pattern

Use a factory pattern to create appropriate extractors for different document types:

```python
class ExtractorFactory:
    @staticmethod
    def create_extractor(document_type):
        if document_type == "pdf":
            return PDFExtractor()
        elif document_type == "docx":
            return DocxExtractor()
        elif document_type == "xlsx":
            return SpreadsheetExtractor()
        # etc.
```

### 4. Tool Registration System

Create a dynamic tool registration system that adapts based on document types:

```python
class ToolRegistry:
    def __init__(self):
        self.tools = {}
        
    def register_tool(self, name, handler, supported_types, schema):
        self.tools[name] = {
            "handler": handler,
            "supported_types": supported_types,
            "schema": schema
        }
        
    def get_available_tools(self, document_type=None):
        if document_type:
            return {name: tool for name, tool in self.tools.items() 
                   if document_type in tool["supported_types"]}
        return self.tools
```

## Migration Strategy

1. **Phase 1: Refactor Current PDF Code**
   - Introduce document handles for PDFs only
   - Refactor extraction code to use handles instead of direct paths
   - Update tool definitions to use the new interface

2. **Phase 2: Abstract Document Interface**
   - Create the base `Document` class and PDF implementation
   - Implement the `DocumentHandlerService`
   - Update server code to use the new abstractions

3. **Phase 3: Add New Document Types**
   - Implement new document type classes (DOCX, XLSX, etc.)
   - Add corresponding extractors
   - Register new document-specific tools

4. **Phase 4: Enhanced Features**
   - Implement cross-document operations (comparison, merging)
   - Add document conversion capabilities
   - Support for more complex extraction options

## Benefits of This Approach

1. **Decoupled Interface**: The LLM interacts with documents through handles, not file paths
2. **Type Agnostic**: Core operations work across document types
3. **Progressive Enhancement**: Document-specific features can be added as needed
4. **Session Management**: Documents are tied to LLM sessions for security and resource management
5. **URI Flexibility**: Support for various document sources (file, data URI, HTTP)

## Challenges to Address

1. **Performance**: Loading large documents could be resource-intensive
2. **Caching Strategy**: Need to balance memory usage with performance
3. **Error Handling**: Different document libraries have different error patterns
4. **Feature Parity**: Ensuring consistent capabilities across document types
5. **Security**: Validating and sanitizing documents from various sources

## Implementation Timeline

The implementation will be phased over several releases:

1. **Q3 2025**: Phase 1 - Refactor Current PDF Code
2. **Q4 2025**: Phase 2 - Abstract Document Interface
3. **Q1 2026**: Phase 3 - Add DOCX and XLSX Support
4. **Q2 2026**: Phase 3 - Add Additional Document Types
5. **Q3 2026**: Phase 4 - Enhanced Features

## Conclusion

This plan outlines a flexible, extensible approach to supporting multiple document types in the Document Understanding MCP Server. By moving to a handle-based interface and abstracting document operations, we can provide a consistent experience for LLMs while accommodating the unique features of different document formats.
