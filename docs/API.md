# Document Understanding MCP Server API Documentation

This document provides comprehensive documentation for the Document Understanding MCP Server API, including available tools, request/response formats, and examples.

## Overview

The Document Understanding MCP Server provides a set of tools for extracting information from PDF documents. It follows the MCP (Model Context Protocol) specification, which defines a standard way for AI models to interact with tools.

## Server Configuration

The server can be configured using environment variables:

| Environment Variable | Description | Default |
|----------------------|-------------|---------|
| `DOCUMENT_UNDERSTANDING_BASE_PATH` | Base path for PDF files | Current working directory |
| `DOCUMENT_UNDERSTANDING_ALLOW_ANY_PATH` | Allow access to files outside the base path | `false` |
| `DOCUMENT_UNDERSTANDING_ENABLE_EXPERIMENTAL` | Enable experimental features | `false` |
| `DOCUMENT_UNDERSTANDING_LOG_LEVEL` | Log level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `DOCUMENT_UNDERSTANDING_LOG_FILE` | Path to log file | None (logs to stderr) |
| `DOCUMENT_UNDERSTANDING_ALLOW_NO_JAVA` | Allow server to run without Java (disables table extraction) | `false` |
| `DOCUMENT_UNDERSTANDING_ALLOW_NO_TESSERACT` | Allow server to run without Tesseract (disables OCR) | `false` |

## Available Tools

The server provides the following tools:

### PDF Metadata Extraction

**Tool Name**: `extract_pdf_metadata`

**Description**: Extracts metadata from a PDF file, including title, author, creation date, and page count.

**Request Parameters**:
- `pdf_path` (string, required): Path to the PDF file
- `password` (string, optional): Password for encrypted PDFs

**Response Format**:
```json
{
  "status": "success",
  "page_count": 10,
  "metadata": {
    "title": "Document Title",
    "author": "Document Author",
    "subject": "Document Subject",
    "keywords": "keyword1, keyword2",
    "creator": "Application that created the PDF",
    "producer": "PDF producer",
    "creation_date": "2023-01-01T00:00:00",
    "modification_date": "2023-01-02T00:00:00"
  },
  "has_embedded_images": true,
  "has_vector_drawings": true
}
```

**Example**:
```json
// Request
{
  "name": "extract_pdf_metadata",
  "arguments": {
    "pdf_path": "documents/sample.pdf"
  }
}

// Response
{
  "status": "success",
  "page_count": 5,
  "metadata": {
    "title": "Sample Document",
    "author": "John Doe",
    "subject": "Sample",
    "keywords": "sample, document",
    "creator": "Microsoft Word",
    "producer": "Adobe PDF Library",
    "creation_date": "2023-01-01T00:00:00",
    "modification_date": "2023-01-02T00:00:00"
  },
  "has_embedded_images": true,
  "has_vector_drawings": false
}
```

### PDF Content Extraction

**Tool Name**: `extract_pdf_contents`

**Description**: Extracts text content from a PDF file.

**Request Parameters**:
- `pdf_path` (string, required): Path to the PDF file
- `pages` (string, optional): Pages to extract (e.g., "1,3-5,7"). If not provided, all pages are extracted.
- `ocr_language` (string, optional): OCR language(s) to use (e.g., 'eng', 'fra+eng'). Only used if OCR is needed. Default is 'eng'.
- `password` (string, optional): Password for encrypted PDFs

**Response Format**:
```json
{
  "status": "success",
  "pages": [
    {
      "page_number": 1,
      "text": "Page 1 content...",
      "error": null
    },
    {
      "page_number": 2,
      "text": "Page 2 content...",
      "error": null
    }
  ],
  "ocr_languages_used": ["eng"]
}
```

**Example**:
```json
// Request
{
  "name": "extract_pdf_contents",
  "arguments": {
    "pdf_path": "documents/sample.pdf",
    "pages": "1-2",
    "ocr_language": "eng"
  }
}

// Response
{
  "status": "success",
  "pages": [
    {
      "page_number": 1,
      "text": "This is the content of page 1.",
      "error": null
    },
    {
      "page_number": 2,
      "text": "This is the content of page 2.",
      "error": null
    }
  ],
  "ocr_languages_used": ["eng"]
}
```

### PDF Image Extraction

**Tool Name**: `extract_images`

**Description**: Extracts images from a PDF file.

**Request Parameters**:
- `pdf_path` (string, required): Path to the PDF file
- `pages` (string, optional): Pages to extract images from (e.g., "1,3-5,7"). If not provided, all pages are processed.
- `include_data` (boolean, optional): Whether to include base64-encoded image data in the response. Default is `false`.
- `min_width` (integer, optional): Minimum image width to include in results.
- `min_height` (integer, optional): Minimum image height to include in results.
- `filter_bbox` (array, optional): Bounding box to filter images by [x0, y0, x1, y1].
- `password` (string, optional): Password for encrypted PDFs

**Response Format**:
```json
{
  "status": "success",
  "images": [
    {
      "page_number": 1,
      "xref": 123,
      "width": 800,
      "height": 600,
      "bbox": {
        "x0": 100,
        "y0": 100,
        "x1": 900,
        "y1": 700
      },
      "data": "base64-encoded-image-data", // Only if include_data is true
      "format": "png" // Only if include_data is true
    }
  ]
}
```

**Example**:
```json
// Request
{
  "name": "extract_images",
  "arguments": {
    "pdf_path": "documents/sample.pdf",
    "pages": "1",
    "include_data": true,
    "min_width": 100,
    "min_height": 100
  }
}

// Response
{
  "status": "success",
  "images": [
    {
      "page_number": 1,
      "xref": 123,
      "width": 800,
      "height": 600,
      "bbox": {
        "x0": 100,
        "y0": 100,
        "x1": 900,
        "y1": 700
      },
      "data": "iVBORw0KGgoAAAANSUhEUgAAA...",
      "format": "png"
    }
  ]
}
```

### PDF Layout Extraction

**Tool Name**: `extract_pdf_layout`

**Description**: Extracts layout information from a PDF file, including text blocks, lines, and spans.

**Request Parameters**:
- `pdf_path` (string, required): Path to the PDF file
- `pages` (string, optional): Pages to extract layout from (e.g., "1,3-5,7"). If not provided, all pages are processed.
- `include_images` (boolean, optional): Whether to include image information in the response. Default is `false`.
- `include_drawings` (boolean, optional): Whether to include vector drawing information in the response. Default is `false`.
- `detail_level` (string, optional): Level of detail to extract. Can be "blocks", "lines", or "words". Default is "blocks".
- `password` (string, optional): Password for encrypted PDFs

**Response Format**:
```json
{
  "status": "success",
  "layout": [
    {
      "page_number": 1,
      "text_blocks": [
        {
          "number": 0,
          "type": 0,
          "bbox": {
            "x0": 100,
            "y0": 100,
            "x1": 500,
            "y1": 150
          },
          "lines": [
            {
              "spans": [
                {
                  "size": 12,
                  "flags": 0,
                  "font": "Arial",
                  "color": 0,
                  "ascender": 0.8,
                  "descender": -0.2,
                  "text": "This is a text span",
                  "origin": {
                    "x": 100,
                    "y": 100
                  },
                  "bbox": {
                    "x0": 100,
                    "y0": 100,
                    "x1": 200,
                    "y1": 120
                  }
                }
              ],
              "wmode": 0,
              "dir": {
                "x": 1,
                "y": 0
              },
              "bbox": {
                "x0": 100,
                "y0": 100,
                "x1": 500,
                "y1": 120
              }
            }
          ]
        }
      ],
      "drawings": [
        {
          "type": 0,
          "items": [
            [
              "re",
              100,
              100,
              400,
              200
            ]
          ],
          "fill": [
            0,
            0,
            0
          ],
          "color": [
            0,
            0,
            0
          ],
          "width": 1.0
        }
      ],
      "images": [
        {
          "xref": 123,
          "bbox": {
            "x0": 100,
            "y0": 100,
            "x1": 300,
            "y1": 200
          },
          "width": 200,
          "height": 100
        }
      ],
      "error": null
    }
  ]
}
```

**Drawings Structure**:
The `drawings` array contains vector drawing elements from the PDF. Each drawing element is a dictionary with the following structure:
- `type`: Drawing type (0 for stroke, 1 for fill, etc.)
- `items`: Array of drawing commands and coordinates
- `fill`: Fill color as [r, g, b] values (0-1 range)
- `color`: Stroke color as [r, g, b] values (0-1 range)
- `width`: Line width

**Images Structure**:
The `images` array contains information about raster images in the PDF. Each image is represented by a `SimpleImageInfo` object with the following structure:
- `xref`: Internal PDF object reference number
- `bbox`: Bounding box of the image on the page (may be null if detection fails)
- `width`: Image width in pixels
- `height`: Image height in pixels

**Example**:
```json
// Request
{
  "name": "extract_pdf_layout",
  "arguments": {
    "pdf_path": "documents/sample.pdf",
    "pages": "1",
    "include_images": true,
    "include_drawings": true,
    "detail_level": "lines"
  }
}

// Response
{
  "status": "success",
  "layout": [
    {
      "page_number": 1,
      "text_blocks": [
        {
          "number": 0,
          "type": 0,
          "bbox": {
            "x0": 100,
            "y0": 100,
            "x1": 500,
            "y1": 150
          },
          "lines": [
            {
              "spans": [
                {
                  "size": 12,
                  "flags": 0,
                  "font": "Arial",
                  "color": 0,
                  "ascender": 0.8,
                  "descender": -0.2,
                  "text": "This",
                  "origin": {
                    "x": 100,
                    "y": 100
                  },
                  "bbox": {
                    "x0": 100,
                    "y0": 100,
                    "x1": 200,
                    "y1": 120
                  }
                },
                {
                  "size": 12,
                  "flags": 0,
                  "font": "Arial",
                  "color": 0,
                  "ascender": 0.8,
                  "descender": -0.2,
                  "text": "is",
                  "origin": {
                    "x": 210,
                    "y": 100
                  },
                  "bbox": {
                    "x0": 210,
                    "y0": 100,
                    "x1": 250,
                    "y1": 120
                  }
                }
              ],
              "wmode": 0,
              "dir": {
                "x": 1,
                "y": 0
              },
              "bbox": {
                "x0": 100,
                "y0": 100,
                "x1": 500,
                "y1": 120
              }
            }
          ]
        }
      ],
      "drawings": [...],
      "images": [...]
    }
  ]
}
```

**Error Handling**:
If an error occurs during layout extraction, the response will include an error message:

```json
{
  "status": "error",
  "message": "Error message",
  "error_code": "ErrorType"
}
```

Additionally, if an error occurs while processing a specific page, that page will still be included in the response with an `error` field:

```json
{
  "status": "success",
  "layout": [
    {
      "page_number": 1,
      "text_blocks": [],
      "error": "Error processing page 1: InvalidPageStructure"
    }
  ]
}
```

### PDF Search

**Tool Name**: `search_pdf_text`

**Description**: Searches for text in a PDF file.

**Request Parameters**:
- `pdf_path` (string, required): Path to the PDF file
- `query` (string, required): Text to search for
- `pages` (string, optional): Pages to search (e.g., "1,3-5,7"). If not provided, all pages are searched.
- `password` (string, optional): Password for encrypted PDFs

**Response Format**:
```json
{
  "status": "success",
  "results": [
    {
      "page": 1,
      "rect": {
        "x0": 100,
        "y0": 100,
        "x1": 300,
        "y1": 120
      }
    }
  ]
}
```

**Example**:
```json
// Request
{
  "name": "search_pdf_text",
  "arguments": {
    "pdf_path": "documents/sample.pdf",
    "query": "example"
  }
}

// Response
{
  "status": "success",
  "results": [
    {
      "page": 1,
      "rect": {
        "x0": 100,
        "y0": 100,
        "x1": 400,
        "y1": 120
      }
    },
    {
      "page": 3,
      "rect": {
        "x0": 200,
        "y0": 300,
        "x1": 500,
        "y1": 320
      }
    }
  ]
}
```

### PDF Table Extraction

**Tool Name**: `extract_tables`

**Description**: Extracts tables from a PDF file.

**Request Parameters**:
- `pdf_path` (string, required): Path to the PDF file
- `pages` (string, optional): Pages to extract tables from (e.g., "1,3-5,7"). If not provided, all pages are processed.
- `password` (string, optional): Password for encrypted PDFs

**Response Format**:
```json
{
  "status": "success",
  "tables": [
    {
      "page_number": 1,
      "table_number": 1,
      "bbox": [100, 100, 500, 300],
      "data": [
        ["Header 1", "Header 2", "Header 3"],
        ["Cell 1,1", "Cell 1,2", "Cell 1,3"],
        ["Cell 2,1", "Cell 2,2", "Cell 2,3"]
      ]
    }
  ]
}
```

**Example**:
```json
// Request
{
  "name": "extract_tables",
  "arguments": {
    "pdf_path": "documents/sample.pdf",
    "pages": "1"
  }
}

// Response
{
  "status": "success",
  "tables": [
    {
      "page_number": 1,
      "table_number": 1,
      "bbox": [100, 200, 500, 400],
      "data": [
        ["Name", "Age", "Location"],
        ["John Doe", "30", "New York"],
        ["Jane Smith", "25", "London"]
      ]
    }
  ]
}
```

### PDF Outline Extraction

**Tool Name**: `extract_pdf_outline`

**Description**: Extracts the outline (table of contents) from a PDF file.

**Request Parameters**:
- `pdf_path` (string, required): Path to the PDF file
- `password` (string, optional): Password for encrypted PDFs

**Response Format**:
```json
{
  "status": "success",
  "outline": [
    {
      "title": "Chapter 1",
      "page_number": 1,
      "level": 1,
      "children": [
        {
          "title": "Section 1.1",
          "page_number": 2,
          "level": 2,
          "children": []
        }
      ]
    }
  ]
}
```

**Example**:
```json
// Request
{
  "name": "extract_pdf_outline",
  "arguments": {
    "pdf_path": "documents/sample.pdf"
  }
}

// Response
{
  "status": "success",
  "outline": [
    {
      "title": "Introduction",
      "page_number": 1,
      "level": 1,
      "children": []
    },
    {
      "title": "Chapter 1",
      "page_number": 3,
      "level": 1,
      "children": [
        {
          "title": "Section 1.1",
          "page_number": 4,
          "level": 2,
          "children": []
        },
        {
          "title": "Section 1.2",
          "page_number": 7,
          "level": 2,
          "children": []
        }
      ]
    }
  ]
}
```

### Get PDF Working Directory

**Tool Name**: `get_pdf_working_directory`

**Description**: Gets the current working directory for PDF files.

**Request Parameters**: None

**Response Format**:
```json
{
  "status": "success",
  "working_directory": "/path/to/working/directory",
  "message": "Restricted to working directory"
}
```

**Example**:
```json
// Request
{
  "name": "get_pdf_working_directory",
  "arguments": {}
}

// Response
{
  "status": "success",
  "working_directory": "/path/to/working/directory",
  "message": "Restricted to working directory"
}
```

### Language Detection

**Tool Name**: `detect_language`

**Description**: Detects the language(s) of text sampled from specified pages.

**Request Parameters**:
- `pdf_path` (string, required): Path to the PDF file
- `pages` (string, optional): Pages to sample text from (e.g., "1,3-5,7"). Default is "1".
- `sample_size` (integer, optional): Maximum number of characters to sample. Default is 2000.
- `password` (string, optional): Password for encrypted PDFs

**Response Format**:
```json
{
  "status": "success",
  "detections": [
    {
      "language_code": "en",
      "confidence": 0.95
    },
    {
      "language_code": "fr",
      "confidence": 0.05
    }
  ],
  "text_sample_used": "Sample text that was used for language detection..."
}
```

**Example**:
```json
// Request
{
  "name": "detect_language",
  "arguments": {
    "pdf_path": "documents/sample.pdf",
    "pages": "1-3",
    "sample_size": 1000
  }
}

// Response
{
  "status": "success",
  "detections": [
    {
      "language_code": "en",
      "confidence": 0.98
    },
    {
      "language_code": "de",
      "confidence": 0.02
    }
  ],
  "text_sample_used": "This is a sample of the text used for language detection..."
}
```

## Error Handling

The server returns error responses in the following format:

```json
{
  "status": "error",
  "message": "Error message",
  "error_code": "ErrorType"
}
```

Common error types include:

- `PDFExtractionError`: General error during PDF extraction
- `PDFPasswordError`: Error when a password is required but not provided or is incorrect
- `FileNotFoundError`: Error when the specified PDF file is not found
- `PermissionError`: Error when the server doesn't have permission to access the file
- `ValidationError`: Error when the request parameters are invalid

## Limitations

- The server currently only supports PDF files
- Table extraction requires Java to be installed
- OCR functionality requires Tesseract to be installed
- Large PDFs may require significant memory and processing time
- Password-protected PDFs require the password to be provided for each operation

## Future Enhancements

See the [plans directory](plans/README.md) for information about planned enhancements, including:

- Support for multiple document types beyond PDF
- Improved handling of large documents
- Enhanced search capabilities
- Better error handling and reporting
