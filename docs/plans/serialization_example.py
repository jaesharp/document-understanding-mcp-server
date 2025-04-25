"""
Example implementation of JSON/XML serialization for Document Understanding tools.

This file demonstrates how the serialization framework would work with actual
response models from the Document Understanding MCP Server.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union, TypeVar, Generic
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pydantic import BaseModel, Field


# --- Sample Response Models ---

class Point(BaseModel):
    x: float
    y: float


class Rect(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class PageContent(BaseModel):
    """Content of a single page."""
    page_number: int = Field(..., description="1-based page number")
    text: str = Field(..., description="Extracted text content")
    error: Optional[str] = None


# Define generic type for response data
T = TypeVar("T")


class BaseToolResponse(BaseModel, Generic[T]):
    """Standard base response model for all tool responses."""
    status: str = "success"
    message: Optional[str] = None
    api_version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Optional[T] = None
    error_code: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class TextContentResponseData(BaseModel):
    """Data container for text content response."""
    pages: List[PageContent]


class TextContentResponse(BaseToolResponse[TextContentResponseData]):
    """Response for text extraction."""
    data: TextContentResponseData


class MetadataResponseData(BaseModel):
    """Data container for metadata response."""
    page_count: int
    metadata: Dict[str, Optional[str]]
    has_embedded_images: Optional[bool] = None
    has_vector_drawings: Optional[bool] = None


class MetadataResponse(BaseToolResponse[MetadataResponseData]):
    """Response for metadata extraction."""
    data: MetadataResponseData


# --- Serialization Framework ---

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
        return response_model.model_dump_json(indent=2)
    
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
        
        # Use minidom to pretty-print the XML
        from xml.dom import minidom
        xml_str = ET.tostring(root, encoding='utf-8')
        pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ")
        
        # Remove the XML declaration added by minidom (we'll add our own)
        if pretty_xml.startswith('<?xml'):
            pretty_xml = pretty_xml.split('\n', 1)[1]
        
        return xml_declaration + pretty_xml
    
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
                # Create a container element for the list
                container = ET.SubElement(parent_element, key)
                
                # Process each item in the list
                for item in value:
                    if isinstance(item, dict):
                        # For dictionaries, use a generic item name
                        item_element = ET.SubElement(container, "Item")
                        SerializationManager._dict_to_xml(item, item_element)
                    elif hasattr(item, "model_dump"):
                        # For Pydantic models, use the model class name
                        item_element = ET.SubElement(container, item.__class__.__name__)
                        SerializationManager._dict_to_xml(item.model_dump(), item_element)
                    else:
                        # For simple values, create an element with the value as text
                        item_element = ET.SubElement(container, "Item")
                        item_element.text = str(item)
            else:
                # Simple values become elements with text content
                child = ET.SubElement(parent_element, key)
                
                # Handle special types
                if isinstance(value, datetime):
                    child.text = value.isoformat() + "Z"
                else:
                    child.text = str(value)


# --- Example Usage ---

def create_sample_responses():
    """Create sample responses for demonstration."""
    
    # Create a metadata response
    metadata_response = MetadataResponse(
        status="success",
        message="Metadata extracted successfully",
        data=MetadataResponseData(
            page_count=42,
            metadata={
                "author": "John Doe",
                "title": "Sample Document",
                "creation_date": "2023-01-15"
            },
            has_embedded_images=True,
            has_vector_drawings=False
        )
    )
    
    # Create a text content response
    text_content_response = TextContentResponse(
        status="success",
        message="Text content extracted successfully",
        data=TextContentResponseData(
            pages=[
                PageContent(
                    page_number=1,
                    text="This is the content of page 1..."
                ),
                PageContent(
                    page_number=2,
                    text="This is the content of page 2..."
                )
            ]
        )
    )
    
    return metadata_response, text_content_response


def demonstrate_serialization():
    """Demonstrate serialization of sample responses."""
    
    metadata_response, text_content_response = create_sample_responses()
    
    print("=== Metadata Response (JSON) ===")
    json_metadata = SerializationManager.serialize(
        metadata_response, SerializationFormat.JSON
    )
    print(json_metadata)
    print("\n")
    
    print("=== Metadata Response (XML) ===")
    xml_metadata = SerializationManager.serialize(
        metadata_response, SerializationFormat.XML
    )
    print(xml_metadata)
    print("\n")
    
    print("=== Text Content Response (JSON) ===")
    json_text = SerializationManager.serialize(
        text_content_response, SerializationFormat.JSON
    )
    print(json_text)
    print("\n")
    
    print("=== Text Content Response (XML) ===")
    xml_text = SerializationManager.serialize(
        text_content_response, SerializationFormat.XML
    )
    print(xml_text)


if __name__ == "__main__":
    demonstrate_serialization()
