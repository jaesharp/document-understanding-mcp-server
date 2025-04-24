# src/document_understanding/standalone_server.py
import argparse
import asyncio
import os
import sys
import logging  # Add basic logging import early
import shutil
import subprocess  # Added for dependency checks # nosec B404 # Reason: Subprocess needed for dependency checks.
from pathlib import Path
from typing import Dict, cast

import structlog

# Correct import: Use Server from mcp.server.lowlevel.server
from mcp.server.lowlevel.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio as mcp_stdio

# Ensure the src directory is in the Python path
# This allows running the script directly for testing/debugging
project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from document_understanding import server as pdf_server  # noqa: E402
from document_understanding.logging_config import (
    configure_logging,
)  # Corrected path noqa: E402
from document_understanding.extractor import PDFExtractor  # noqa: E402

# Debug line to print the file being executed
print(f"DEBUG: Executing standalone_server.py at {__file__}", file=sys.stderr)

# --- Global Server Capabilities ---
# Populated based on checks and config
SERVER_CAPABILITIES: Dict[str, bool] = {
    "java_runtime": False,
    "tesseract_ocr": False,
    "experimental_features": False,
    "search_functionality": True,  # Assume search is available unless disabled
}

# --- Dependency Check Functions ---


def check_java_runtime(ignore_missing: bool = False) -> bool:
    """Checks for Java runtime (required for extract_tables)."""
    # 1. Check JAVA_HOME env var
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        java_exe = Path(java_home) / "bin" / "java"
        if java_exe.is_file() and os.access(java_exe, os.X_OK):
            # Check if it runs
            try:
                # Use timeout to prevent hangs if java is broken
                result = subprocess.run(  # nosec B603 # Reason: Fixed command ("java", "-version") for dependency check, not user input.
                    [str(java_exe), "-version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )  # Use check=False
                if result.returncode == 0 and (
                    "version" in result.stderr or "version" in result.stdout
                ):
                    print(
                        f"STANDALONE_SERVER: Java found via JAVA_HOME: {java_exe}",
                        file=sys.stderr,
                    )
                    return True
                else:
                    print(
                        f"STANDALONE_SERVER: Java found via JAVA_HOME ({java_exe}) but '-version' failed (RC={result.returncode}).",
                        file=sys.stderr,
                    )
                    # Continue to check PATH
            except (subprocess.TimeoutExpired, Exception) as e:
                print(
                    f"STANDALONE_SERVER: Error checking Java from JAVA_HOME ({java_exe}): {e}",
                    file=sys.stderr,
                )
                # Continue to check PATH

    # 2. Check PATH using shutil.which
    java_path = shutil.which("java")
    if java_path:
        # Check if it runs
        try:
            result = subprocess.run(  # nosec B603 # Reason: Fixed command ("java", "-version") for dependency check, not user input.
                [java_path, "-version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )  # Use check=False
            if result.returncode == 0 and (
                "version" in result.stderr or "version" in result.stdout
            ):
                print(
                    f"STANDALONE_SERVER: Java found via PATH: {java_path}",
                    file=sys.stderr,
                )
                return True
            else:
                print(
                    f"STANDALONE_SERVER: Java found via PATH ({java_path}) but '-version' failed (RC={result.returncode}).",
                    file=sys.stderr,
                )
                return False  # If found in PATH but broken, treat as missing unless ignored
        except (subprocess.TimeoutExpired, Exception) as e:
            print(
                f"STANDALONE_SERVER: Error checking Java from PATH ({java_path}): {e}",
                file=sys.stderr,
            )
            return False  # Treat error as missing unless ignored

    # If not found
    if ignore_missing:
        print(
            "STANDALONE_SERVER: Java runtime not found, but ignoring.", file=sys.stderr
        )
        return False
    else:
        print(
            "STANDALONE_SERVER: ERROR: Java runtime not found. Needed for 'extract_tables'. Set JAVA_HOME or ensure 'java' is in PATH.",
            file=sys.stderr,
        )
        return False  # Return False if not found and not ignored


def check_tesseract(ignore_missing: bool = False) -> bool:
    """Checks for Tesseract OCR."""
    # 1. Check TESSERACT_HOME env var
    tesseract_home = os.environ.get("TESSERACT_HOME")
    if tesseract_home:
        tesseract_exe = Path(tesseract_home) / "bin" / "tesseract"
        if tesseract_exe.is_file() and os.access(tesseract_exe, os.X_OK):
            try:
                result = subprocess.run(  # nosec B603 # Reason: Fixed command ("tesseract", "--version") for dependency check, not user input.
                    [str(tesseract_exe), "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if result.returncode == 0 and "tesseract" in result.stdout:
                    print(
                        f"STANDALONE_SERVER: Tesseract found via TESSERACT_HOME: {tesseract_exe}",
                        file=sys.stderr,
                    )
                    return True
                else:
                    print(
                        f"STANDALONE_SERVER: Tesseract found via TESSERACT_HOME ({tesseract_exe}) but '--version' failed (RC={result.returncode}).",
                        file=sys.stderr,
                    )
            except (subprocess.TimeoutExpired, Exception) as e:
                print(
                    f"STANDALONE_SERVER: Error checking Tesseract from TESSERACT_HOME ({tesseract_exe}): {e}",
                    file=sys.stderr,
                )

    # 2. Check PATH using shutil.which
    tesseract_path = shutil.which("tesseract")
    if tesseract_path:
        try:
            result = subprocess.run(  # nosec B603 # Reason: Fixed command ("tesseract", "--version") for dependency check, not user input.
                [tesseract_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0 and "tesseract" in result.stdout:
                print(
                    f"STANDALONE_SERVER: Tesseract found via PATH: {tesseract_path}",
                    file=sys.stderr,
                )
                return True
            else:
                print(
                    f"STANDALONE_SERVER: Tesseract found via PATH ({tesseract_path}) but '--version' failed (RC={result.returncode}).",
                    file=sys.stderr,
                )
                return False
        except (subprocess.TimeoutExpired, Exception) as e:
            print(
                f"STANDALONE_SERVER: Error checking Tesseract from PATH ({tesseract_path}): {e}",
                file=sys.stderr,
            )
            return False

    # If not found
    if ignore_missing:
        print("STANDALONE_SERVER: Tesseract not found, but ignoring.", file=sys.stderr)
        return False
    else:
        print(
            "STANDALONE_SERVER: WARNING: Tesseract OCR not found. OCR capabilities will be limited.",
            file=sys.stderr,
        )
        return False  # Return False if not found and not ignored


# --- Main Execution ---
def main():
    # *** ADDED LOGGING START ***
    print("STANDALONE_SERVER: main() entered", file=sys.stderr)
    try:
        # Minimal logging setup to capture early errors before full config
        # Log to stderr initially
        logging.basicConfig(
            level=logging.DEBUG,
            stream=sys.stderr,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        early_logger = logging.getLogger("standalone_server_early")
        early_logger.info("STANDALONE_SERVER: Early logging configured to stderr.")
    except Exception as e:
        print(
            f"STANDALONE_SERVER: FAILED to configure early logging: {e}",
            file=sys.stderr,
        )
        sys.exit(1)  # Exit early if basic logging fails
    # *** ADDED LOGGING END ***

    parser = argparse.ArgumentParser(
        description="Document Understanding MCP Tool Server"
    )
    parser.add_argument("--log-level", type=str, default="INFO", help="Logging level")
    parser.add_argument("--log-file", type=str, default=None, help="Logging file")
    parser.add_argument(
        "--log-file-level", type=str, default="INFO", help="Logging file level"
    )
    parser.add_argument(
        "--ignore-missing-dependencies",
        type=str,
        default="",
        help="Comma-separated list of dependencies to ignore",
    )
    parser.add_argument(
        "--enable-experimental",
        action="store_true",
        help="Enable experimental features",
    )
    parser.add_argument(
        "--disable-search", action="store_true", help="Disable search functionality"
    )
    parser.add_argument(
        "--allow-any-path", action="store_true", help="Allow access to any path"
    )
    parser.add_argument(
        "--base-path", type=str, help="Restrict file access to a specific base path"
    )
    try:
        args = parser.parse_args()
        early_logger.info(
            f"STANDALONE_SERVER: Arguments parsed: {args}"
        )  # Log parsed args

        # Early check for conflicting configuration
        base_path_env = os.environ.get("DOCUMENT_UNDERSTANDING_BASE_PATH")
        if args.allow_any_path and base_path_env:
            error_msg = "Cannot use --allow-any-path flag when DOCUMENT_UNDERSTANDING_BASE_PATH environment variable is also set."
            early_logger.error(f"STANDALONE_SERVER: {error_msg}")
            print(f"ERROR: {error_msg}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        early_logger.error(
            f"STANDALONE_SERVER: Argument parsing failed: {e}", exc_info=True
        )

    try:
        # Configure logging using settings
        from .logging_config import configure_logging

        configure_logging()
        # Get structlog logger *after* configuration
        logger = cast(
            structlog.stdlib.BoundLogger, structlog.get_logger("standalone_server")
        )
        logger.info("STANDALONE_SERVER: Structlog logging configured.")
    except Exception as e:
        # Use early_logger if structlog failed
        early_logger.error(
            f"STANDALONE_SERVER: FAILED configure_logging: {e}", exc_info=True
        )
        print(
            f"STANDALONE_SERVER: FAILED configure_logging: {e}", file=sys.stderr
        )  # Fallback print
        sys.exit(1)

    # --- Dependency Checks & Capability Setting ---
    logger.info("STANDALONE_SERVER: Checking dependencies...")
    try:
        ignore_list = [
            dep.strip()
            for dep in args.ignore_missing_dependencies.split(",")
            if dep.strip()
        ]
        logger.debug(f"Ignoring missing dependencies: {ignore_list}")

        SERVER_CAPABILITIES["java_runtime"] = check_java_runtime(
            ignore_missing="java_runtime" in ignore_list
        )
        SERVER_CAPABILITIES["tesseract_ocr"] = check_tesseract(
            ignore_missing="tesseract_ocr" in ignore_list
        )
        SERVER_CAPABILITIES["experimental_features"] = args.enable_experimental
        SERVER_CAPABILITIES["search_functionality"] = not args.disable_search

        # Update server module capabilities
        pdf_server.SERVER_CAPABILITIES.update(SERVER_CAPABILITIES)
        logger.info(
            f"STANDALONE_SERVER: Final capabilities set: {pdf_server.SERVER_CAPABILITIES}"
        )

    except Exception:
        logger.error(
            "STANDALONE_SERVER: FAILED during capability checks", exc_info=True
        )
        sys.exit(1)

    # --- Server Setup ---
    logger.info("STANDALONE_SERVER: Configuring server...")
    try:
        # --- Check for conflicting configuration ---
        base_path_env = os.environ.get("DOCUMENT_UNDERSTANDING_BASE_PATH")
        if args.allow_any_path and base_path_env:
            error_msg = "Cannot use --allow-any-path flag when DOCUMENT_UNDERSTANDING_BASE_PATH environment variable is also set."
            logger.error(f"STANDALONE_SERVER: {error_msg}")
            print(f"ERROR: {error_msg}", file=sys.stderr)
            sys.exit(1)

        # --- Configure Base Path ---
        if args.allow_any_path:
            pdf_server.ALLOW_ANY_PATH = True
            pdf_server.BASE_PATH = None
            logger.warning("Server configured to allow access to any path.")
        else:
            pdf_server.ALLOW_ANY_PATH = False
            if args.base_path:
                resolved_base_path = str(Path(args.base_path).resolve())
                pdf_server.BASE_PATH = resolved_base_path
                logger.info(
                    f"Restricting file access to base path: {resolved_base_path}"
                )
            else:
                # Default to current working directory if --base-path not set and --allow-any-path is false
                default_base_path = str(Path.cwd().resolve())
                pdf_server.BASE_PATH = default_base_path
                logger.info(
                    f"Restricting file access to default base path (cwd): {default_base_path}"
                )

        # --- Instantiate Extractor and Server ---
        # Instantiate PDFExtractor *after* capabilities affecting it might be known
        pdf_server.extractor = (
            PDFExtractor()
        )  # Ensure extractor instance exists in the server module
        logger.info("STANDALONE_SERVER: PDFExtractor instantiated.")

        # Instantiate the NEW mcp.Server (handlers are registered via decorators in server.py)
        # We use the pdf_server instance which should already have handlers decorated.
        mcp_server_instance: Server = (
            pdf_server.server
        )  # Use the server instance from the pdf_server module
        logger.info(
            f"STANDALONE_SERVER: Using MCP Server instance from pdf_server module: {mcp_server_instance.name}"
        )

        # --- Create Initialization Options ---
        init_options: InitializationOptions = (
            mcp_server_instance.create_initialization_options(
                # Use None for notification options
                notification_options=None,
                experimental_capabilities={},  # Define any experimental caps if needed
            )
        )
        logger.debug(f"InitializationOptions created: {init_options}")

    except Exception:
        logger.error("STANDALONE_SERVER: FAILED during server setup", exc_info=True)
        sys.exit(1)

    # --- Run Server ---
    logger.info("STANDALONE_SERVER: Starting server run loop...")
    try:
        # Use asyncio.run() with the stdio_server context manager
        # and pass streams/options to the mcp_server_instance.run method
        async def run_server_main_func():
            async with mcp_stdio.stdio_server() as (read_stream, write_stream):
                logger.info("stdio_server context entered. Calling server.run...")
                await mcp_server_instance.run(
                    read_stream,
                    write_stream,
                    init_options,
                    # raise_exceptions=True # Optional for debugging
                )
                logger.info(
                    "mcp_server_instance.run finished."
                )  # Should not normally be reached

        asyncio.run(run_server_main_func())
        logger.info(
            "STANDALONE_SERVER: Server run loop finished."
        )  # Should not be reached normally
    except Exception:
        logger.error("STANDALONE_SERVER: Server run loop FAILED", exc_info=True)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info(
            "STANDALONE_SERVER: Server interrupted by KeyboardInterrupt. Exiting."
        )
        sys.exit(0)  # Exit gracefully on Ctrl+C

    logger.info("STANDALONE_SERVER: Exiting.")
    sys.exit(0)  # Explicit exit at the end


if __name__ == "__main__":
    # Add a print statement right before calling main
    print("STANDALONE_SERVER: Script entry point (__main__) reached.", file=sys.stderr)

    main()
