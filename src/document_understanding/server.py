import sys
import json
from mcp.server.models import InitializationOptions
import mcp.types as mcp_types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import functools
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union, TypeVar, Protocol, overload, Literal, cast
from datetime import datetime

from .extractor import PDFExtractor
from .logging_config import configure_logging, get_logger
from .path_validator import PathValidator
from .error_handler import handle_tool_errors, serialize_response_data
from .schemas import get_schema_dict
from . import handlers as tool_handlers

# Import response models
from .models import (
    MetadataResponse,
    TextContentResponse,
    SearchResponse,
    LayoutResponse,
    SearchResult,  # noqa: F401 - Used in type annotations & handlers
    Rect as RectModel,  # noqa: F401 - Used in type annotations & handlers
    ImageExtractionResponse,
    ImageDescriptor,  # noqa: F401 - Used in type annotations & handlers
    SimpleImageInfo,  # noqa: F401 - Used in type annotations & handlers
    PageContent,  # noqa: F401 - Used in type annotations & handlers
    TableExtractionResponse,
    Table,  # noqa: F401 - Used in type annotations & handlers
    LanguageDetectionResponse,
    LanguageDetection,  # noqa: F401 - Used in type annotations & handlers
    OutlineResponse,
    PageLayout,  # noqa: F401 - Used in type annotations & handlers
    WorkingDirectoryResponse,
    ErrorResponse,
    BaseToolResponse,
)

# Configure logging as early as possible
configure_logging()
logger = get_logger(__name__)

# Global state
global_context_settings: Dict[str, Any] = {}
SERVER_CAPABILITIES: Dict[str, bool] = {}
ALLOW_ANY_PATH: bool = False  # Populated by standalone_server
BASE_PATH: Optional[str] = None  # Populated by standalone_server

# --- Tool Schema Definitions ---
# Common parameter definitions for reuse
PDF_PATH_PARAM = {
    "type": "string",
    "description": "Path relative to working dir, or absolute if allowed.",
}

PAGES_PARAM = {
    "type": "string",
    "description": "Optional: Page spec (1-based, ranges, neg indices). Default=all.",
}

PASSWORD_PARAM = {
    "type": "string",
    "description": "Optional: Password for encrypted PDFs.",
}

# Type aliases for handler functions
ToolHandlerResult = Union[
    TextContentResponse,
    LayoutResponse,
    MetadataResponse,
    SearchResponse,
    ImageExtractionResponse,
    TableExtractionResponse,
    LanguageDetectionResponse,
    OutlineResponse,
    WorkingDirectoryResponse,
]

# Define handler function types
class PDFRequiredHandlerProtocol(Protocol):
    """Protocol for tool handlers that require a PDF path."""
    def __call__(
        self, arguments: Dict[str, Any], validated_pdf_path: str, pages_str: Optional[str]
    ) -> ToolHandlerResult: ...

class PDFOptionalHandlerProtocol(Protocol):
    """Protocol for tool handlers that do not require a PDF path."""
    def __call__(
        self, arguments: Dict[str, Any], validated_pdf_path: Optional[str], pages_str: Optional[str]
    ) -> ToolHandlerResult: ...

# Either type of handler can be registered
ToolHandlerFunction = Union[PDFRequiredHandlerProtocol, PDFOptionalHandlerProtocol]

# Definition of all tool descriptions and schemas
@dataclass
class ToolDefinition:
    """Data class for tool metadata and schemas"""

    name: str
    base_description: str
    guidance: str = ""
    required_capabilities: List[str] = field(default_factory=list)
    conditional_description: Optional[Callable[[Dict[str, bool]], str]] = None
    input_schema: Dict[str, Any] = field(default_factory=dict)
    exclude_when: Optional[Callable[[Dict[str, bool], bool], bool]] = None

    def get_description(self, capabilities: Dict[str, bool]) -> str:
        """Build the full description based on capabilities"""
        desc = self.base_description

        if self.conditional_description:
            conditional_text = self.conditional_description(capabilities)
            if conditional_text:
                desc += " " + conditional_text

        if self.guidance:
            desc += " Guidance: " + self.guidance

        return desc

    def should_exclude(
        self, capabilities: Dict[str, bool], allow_any_path: bool
    ) -> bool:
        """Determine if this tool should be excluded based on current settings"""
        if self.exclude_when and self.exclude_when(capabilities, allow_any_path):
            return True

        # Check if all required capabilities are available
        if self.required_capabilities:
            for cap in self.required_capabilities:
                if not capabilities.get(cap, False):
                    return True

        return False

    def create_tool(self, capabilities: Dict[str, bool]) -> mcp_types.Tool:
        """Create a Tool instance with the appropriate configuration"""
        return mcp_types.Tool(
            name=self.name,
            description=self.get_description(capabilities),
            inputSchema=self.input_schema,
        )


# Tool registry to manage both definitions and handlers
class ToolRegistry:
    """Registry for tool definitions and handlers"""

    def __init__(self):
        self._definitions: Dict[str, ToolDefinition] = {}
        self._handlers: Dict[str, ToolHandlerFunction] = {}
        # Moved from global TOOL_CAPABILITIES_REQUIRED
        self._legacy_capability_requirements: Dict[str, List[str]] = {
            "extract_tables": ["java_runtime"],
            "find_nearby_content": ["experimental_features"],
            "search_pdf_text": ["search_functionality"],
        }

    def register(
        self, definition: ToolDefinition, handler: ToolHandlerFunction
    ) -> None:
        """Register both a tool definition and its handler"""
        self._definitions[definition.name] = definition
        self._handlers[definition.name] = handler

    def get_handler(self, name: str) -> Optional[ToolHandlerFunction]:
        """Get handler for a tool by name"""
        return self._handlers.get(name)

    def get_definition(self, name: str) -> Optional[ToolDefinition]:
        """Get definition for a tool by name"""
        return self._definitions.get(name)

    def check_capabilities(self, name: str, capabilities: Dict[str, bool]) -> List[str]:
        """
        Check if the required capabilities for a tool are available.
        Returns a list of missing capabilities (empty if all requirements are met).

        This checks both:
        1. The tool definition's required_capabilities list
        2. The legacy_capability_requirements dictionary (for backward compatibility)
        """
        missing_caps = []

        # Check capabilities from the tool definition
        definition = self.get_definition(name)
        if definition:
            for cap in definition.required_capabilities:
                if not capabilities.get(cap, False):
                    missing_caps.append(cap)

        # Also check legacy requirements for backward compatibility
        legacy_requirements = self._legacy_capability_requirements.get(name, [])
        for cap in legacy_requirements:
            if cap not in missing_caps and not capabilities.get(cap, False):
                missing_caps.append(cap)

        return missing_caps

    def list_tools(
        self, capabilities: Dict[str, bool], allow_any_path: bool
    ) -> List[mcp_types.Tool]:
        """List all available tools based on capabilities and settings"""
        available_tools = []

        for name, tool_def in self._definitions.items():
            if tool_def.should_exclude(capabilities, allow_any_path):
                logger.debug(
                    f"Tool '{tool_def.name}' disabled due to missing capabilities or settings"
                )
                continue

            # Additional check for legacy capability requirements
            has_missing_legacy_capabilities = False
            legacy_requirements = self._legacy_capability_requirements.get(name, [])
            for cap in legacy_requirements:
                if not capabilities.get(cap, False):
                    has_missing_legacy_capabilities = True
                    logger.debug(
                        f"Tool '{tool_def.name}' disabled due to missing legacy capability: {cap}"
                    )
                    break

            if has_missing_legacy_capabilities:
                continue

            available_tools.append(tool_def.create_tool(capabilities))

        return available_tools


# Initialize the global tool registry
tool_registry = ToolRegistry()

# Initialize the path validator
path_validator = None


def initialize_server_components():
    """Initialize server components after settings are loaded"""
    global path_validator

    # Initialize the path validator
    path_validator = PathValidator(BASE_PATH, ALLOW_ANY_PATH)

    # Initialize the handlers module
    tool_handlers.initialize(get_extractor(), BASE_PATH, ALLOW_ANY_PATH)


# Function decorator to register tools with proper typing
@overload
def register_tool(
    name: str,
    base_description: str,
    guidance: str = "",
    required_capabilities: List[str] = [],
    conditional_description: Optional[Callable[[Dict[str, bool]], str]] = None,
    input_schema: Dict[str, Any] = {},
    exclude_when: Optional[Callable[[Dict[str, bool], bool], bool]] = None,
    requires_pdf_path: Literal[True] = True,
) -> Callable[[PDFRequiredHandlerProtocol], PDFRequiredHandlerProtocol]: ...

@overload
def register_tool(
    name: str,
    base_description: str,
    guidance: str = "",
    required_capabilities: List[str] = [],
    conditional_description: Optional[Callable[[Dict[str, bool]], str]] = None,
    input_schema: Dict[str, Any] = {},
    exclude_when: Optional[Callable[[Dict[str, bool], bool], bool]] = None,
    requires_pdf_path: Literal[False] = False,
) -> Callable[[PDFOptionalHandlerProtocol], PDFOptionalHandlerProtocol]: ...

def register_tool(
    name: str,
    base_description: str,
    guidance: str = "",
    required_capabilities: List[str] = [],
    conditional_description: Optional[Callable[[Dict[str, bool]], str]] = None,
    input_schema: Dict[str, Any] = {},
    exclude_when: Optional[Callable[[Dict[str, bool], bool], bool]] = None,
    requires_pdf_path: bool = True,
):
    """
    Decorator to register a tool handler function along with its definition.
    """
    # Create the tool definition
    tool_def = ToolDefinition(
        name=name,
        base_description=base_description,
        guidance=guidance,
        required_capabilities=required_capabilities,
        conditional_description=conditional_description,
        input_schema=input_schema or get_schema_dict(name),
        exclude_when=exclude_when,
    )

    def decorator(
        func: Union[PDFRequiredHandlerProtocol, PDFOptionalHandlerProtocol],
    ) -> Union[PDFRequiredHandlerProtocol, PDFOptionalHandlerProtocol]:
        """Register a tool handler with appropriate type checking."""
        
        @functools.wraps(func)
        def wrapper(
            arguments: Dict[str, Any],
            validated_pdf_path: Optional[str],
            pages_str: Optional[str],
        ) -> ToolHandlerResult:
            """Wrapper that enforces PDF path requirements."""
            if requires_pdf_path and validated_pdf_path is None:
                raise ValueError(f"pdf_path is required for {name}")

            # Safe to call the function now
            if requires_pdf_path:
                # We know validated_pdf_path is not None at this point
                return cast(PDFRequiredHandlerProtocol, func)(
                    arguments, cast(str, validated_pdf_path), pages_str
                )
            else:
                return cast(PDFOptionalHandlerProtocol, func)(
                    arguments, validated_pdf_path, pages_str
                )

        # Register both the definition and handler
        tool_registry.register(tool_def, wrapper)
        return func  # Return the original function for clarity

    return decorator


# MCP Server Configuration
server: Server = Server("document-understanding")

# Lazy initialization
extractor: Optional[PDFExtractor] = None


# --- Lazy Extractor Instantiation ---
def get_extractor() -> PDFExtractor:
    """Gets the extractor instance, creating it if necessary using global capabilities."""
    global extractor
    if extractor is None:
        logger.info("Creating default PDFExtractor instance (lazy)...")
        if not SERVER_CAPABILITIES:
            logger.warning(
                "SERVER_CAPABILITIES not populated when creating extractor. Using defaults."
            )
            extractor = PDFExtractor(capabilities={})
        else:
            extractor = PDFExtractor(capabilities=SERVER_CAPABILITIES)
        logger.info(
            f"PDFExtractor instance created with capabilities: {extractor.capabilities}"
        )
    return extractor


# Flag set by standalone_server.py based on startup check
# JAVA_AVAILABLE = True # Replaced by SERVER_CAPABILITIES


# Helper to get current context setting or default
def get_context_setting(key: str, default: Any) -> Any:
    return default


@server.list_tools()
async def handle_list_tools() -> list[mcp_types.Tool]:
    """Define available tools, dynamically filtering and adding guidance."""

    # Use the registry to list tools
    available_tools = tool_registry.list_tools(SERVER_CAPABILITIES, ALLOW_ANY_PATH)

    # === DEBUGGING PRINT ===
    logger.debug(f"Returning tools: {[t.name for t in available_tools]}")
    return available_tools


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[mcp_types.TextContent]:
    """
    Handle tool calls based on the provided tool name and arguments.
    Dispatches to the appropriate PDFExtractor method after validation.
    """
    if arguments is None:
        arguments = {}

    logger.info(f"Handling tool call: {name}", arguments=arguments)

    # Check if the requested tool is supported
    handler = tool_registry.get_handler(name)
    if not handler:
        error_response = ErrorResponse(
            status="error",
            error_code="unknown_tool",
            message=f"Unknown or unavailable tool: {name}",
            error_details={"tool_name": name},
        )
        response_json = json.dumps(
            error_response.model_dump(),
            default=lambda o: o.isoformat() + "Z" if isinstance(o, datetime) else None,
        )
        return [mcp_types.TextContent(text=response_json, type="text")]

    # Capability Check using the registry
    missing_caps = tool_registry.check_capabilities(name, SERVER_CAPABILITIES)
    if missing_caps:
        error_response = ErrorResponse(
            status="error",
            error_code="missing_capabilities",
            message=f"Cannot execute tool '{name}'. Required capabilities missing: {missing_caps}",
            error_details={"tool_name": name, "missing_capabilities": missing_caps},
        )
        response_json = json.dumps(
            error_response.model_dump(),
            default=lambda o: o.isoformat() + "Z" if isinstance(o, datetime) else None,
        )
        return [mcp_types.TextContent(text=response_json, type="text")]

    # Always initialize components on each call to ensure we have the latest configuration
    # This is important for tests where BASE_PATH and ALLOW_ANY_PATH are patched between calls
    initialize_server_components()

    # Apply error handling decorator to the handler execution
    @handle_tool_errors(name, arguments)
    def execute_handler():
        # Ensure path_validator is initialized
        if path_validator is None:
            # Make sure components are initialized
            initialize_server_components()
            if path_validator is None:
                # If still None, there's a critical initialization error
                raise RuntimeError(
                    "PathValidator initialization failed - server components not properly initialized"
                )

        # Argument Validation - always run this regardless of whether it's a test or not
        validated_pdf_path, pages_str = path_validator.validate_and_prepare_args(
            name, arguments
        )

        # Check if this tool requires a PDF path
        tool_def = tool_registry.get_definition(name)
        requires_pdf = False
        if tool_def:
            # Look through registered tools to find if this one requires a PDF path
            for param_name, param_info in tool_def.input_schema.get("properties", {}).items():
                if param_name == "pdf_path" and param_info.get("required", False):
                    requires_pdf = True
                    break

        # Call the handler - same code path for tests and production
        if requires_pdf:
            if validated_pdf_path is None:
                raise ValueError(f"PDF path is required for tool '{name}'")
            # Cast to help the type checker
            pdf_handler = cast(PDFRequiredHandlerProtocol, handler)
            return pdf_handler(arguments, cast(str, validated_pdf_path), pages_str)
        else:
            # This tool doesn't require a PDF path, so it's fine to pass None
            pdf_optional_handler = cast(PDFOptionalHandlerProtocol, handler)
            return pdf_optional_handler(arguments, validated_pdf_path, pages_str)

    # Execute handler and serialize response
    response_data = execute_handler()

    # Check if the response is an ErrorResponse (from our error handler)
    if isinstance(response_data, ErrorResponse):
        # Already an error response, so just serialize it
        response_json = json.dumps(
            response_data.model_dump(),
            default=lambda o: o.isoformat() + "Z" if isinstance(o, datetime) else None,
        )
    elif isinstance(response_data, BaseToolResponse):
        # Normal tool response, serialize it
        response_json = serialize_response_data(name, response_data)
        logger.debug(f"Tool '{name}' executed successfully.")
    else:
        # Unexpected response type
        logger.error(
            f"Unexpected response type from tool '{name}': {type(response_data)}"
        )
        error_response = ErrorResponse(
            status="error",
            error_code="invalid_response",
            message=f"Tool '{name}' returned an invalid response type",
            error_details={
                "tool_name": name,
                "response_type": str(type(response_data)),
            },
        )
        response_json = json.dumps(
            error_response.model_dump(),
            default=lambda o: o.isoformat() + "Z" if isinstance(o, datetime) else None,
        )

    return [mcp_types.TextContent(text=response_json, type="text")]


# Register the handlers from the handlers module
def register_handlers():
    """Register all tool handlers"""

    # Extract text handler
    register_tool(
        "extract_pdf_contents",
        (
            "Extracts text content from specified pages of a local PDF file. "
            "Uses direct text extraction with OCR fallback."
        ),
        conditional_description=lambda caps: (
            "NOTE: OCR capability (Tesseract) is disabled."
            if not caps.get("tesseract_ocr", False)
            else ""
        ),
        requires_pdf_path=True,
    )(tool_handlers.handle_extract_text)

    # Extract layout handler
    register_tool(
        "extract_pdf_layout",
        "Extracts detailed layout info: text blocks, drawings, image placements with coordinates.",
        "Use for spatial analysis. Can be large output.",
        requires_pdf_path=True,
    )(tool_handlers.handle_extract_layout)

    # Extract metadata handler
    register_tool(
        "extract_pdf_metadata",
        "Extracts metadata (author, title, dates) and checks for images/drawings.",
        "Good first step to understand PDF.",
        requires_pdf_path=True,
    )(tool_handlers.handle_extract_metadata)

    # Search text handler
    register_tool(
        "search_pdf_text",
        "Searches for exact text (case-sensitive) within specified pages and returns bounding boxes.",
        "Use for finding specific terms.",
        required_capabilities=["search_functionality"],
        requires_pdf_path=True,
    )(tool_handlers.handle_search_text)

    # Extract images handler
    register_tool(
        "extract_images",
        "(EXPERIMENTAL) Extracts info about images (raster, forms). Bbox is optional.",
        "bbox optional. Use include_data cautiously.",
        requires_pdf_path=True,
    )(tool_handlers.handle_extract_images)

    # Extract tables handler
    register_tool(
        "extract_tables",
        "Extracts tables from specified pages into lists of lists.",
        required_capabilities=["java_runtime"],
        conditional_description=lambda caps: (
            "NOTE: Requires Java runtime, which is currently unavailable."
            if not caps.get("java_runtime", False)
            else "(Requires Java runtime)."
        ),
        requires_pdf_path=True,
    )(tool_handlers.handle_extract_tables)

    # Detect language handler
    register_tool(
        "detect_language",
        "Detects language(s) of text sampled from specified pages.",
        "Useful before OCR/translation.",
        requires_pdf_path=True,
    )(tool_handlers.handle_detect_language)

    # Extract outline handler
    register_tool(
        "extract_pdf_outline",
        "Extracts the document outline (Table of Contents/Bookmarks).",
        "Useful for navigating large PDFs.",
        requires_pdf_path=True,
    )(tool_handlers.handle_extract_pdf_outline)

    # Get working directory handler
    register_tool(
        "get_pdf_working_directory",
        "Returns the designated directory path for placing PDFs.",
        "Use before needing to provide a pdf_path.",
        exclude_when=lambda caps, allow_any_path: allow_any_path,
        requires_pdf_path=False,
    )(tool_handlers.handle_get_pdf_working_directory)


# Register handlers when module is loaded
register_handlers()


# Main startup function
async def main():
    # Logging is already configured
    logger.info(
        "Starting Document Understanding MCP server (inside main)..."
    )  # Keep this info log
    print(
        "DEBUG: server.py main() reached, about to enter stdio context.",
        file=sys.stderr,
    )
    # Run the server using stdin/stdout streams
    try:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            print(
                "DEBUG: server.py main() entered stdio context successfully.",
                file=sys.stderr,
            )
            logger.info(
                "stdio_server context entered. Calling server.run..."
            )  # Keep this info log
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="document-understanding",
                    server_version="0.1.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
                # raise_exceptions=True # Optional for debugging
            )
            # logger.debug(f"InitializationOptions prepared: {init_options}") # init_options is not defined here
            logger.info(
                "server.run completed (should not happen in normal stdio operation unless client disconnects)"
            )  # Add exit log
    except Exception:
        logger.exception(
            "Error during server main execution (outer try block)"
        )  # Log exception explicitly
        # Decide if re-raising is needed - for testing, maybe not to see if mcpt gets *any* output
        # raise
    finally:
        logger.info("Exiting server main function.")  # Ensure this logs
