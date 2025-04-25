#!/usr/bin/env python3
"""
Command-line interface entry point for document understanding MCP server.
Provides a clean Python entry point for the package when installed.
"""

import argparse
import json
import logging
import os
import sys
import tempfile
import traceback
from enum import Enum, auto
from typing import Any, Dict, Optional, Tuple

from document_understanding.standalone_server import main as server_main


def cli_main():
    """
    Main entry point for document-understanding-mcp-server command.
    Sets up environment variables, processes arguments, and calls the main server function.
    """
    # Set default environment variables if not already set
    os.environ.setdefault("PYTHONUNBUFFERED", "1")

    # Set sandbox mode by default (more secure)
    sandbox_mode = (
        os.environ.setdefault("DOCUMENT_UNDERSTANDING_SANDBOX", "true").lower()
        == "true"
    )

    # Enable saving images to files if not already set
    os.environ.setdefault("ENABLE_SAVE_IMAGES_TO_FILES", "true")

    # If sandbox mode is enabled, create safe directories
    if sandbox_mode:
        if not os.environ.get("SAFE_OUTPUT_DIRECTORIES"):
            # Create a user-specific safe location
            xdg_runtime = os.environ.get("XDG_RUNTIME_DIR")
            user = os.environ.get("USER", "user")

            if xdg_runtime:
                safe_dir = os.path.join(xdg_runtime, f"document_understanding_{user}")
            else:
                # Use tempfile.gettempdir() instead of hardcoded /tmp
                temp_base = tempfile.gettempdir()
                safe_dir = os.path.join(temp_base, f"document_understanding_{user}")

            os.environ["SAFE_OUTPUT_DIRECTORIES"] = safe_dir
            print(f"Sandbox mode: Setting safe output directory to {safe_dir}")

            # Create the output directory
            os.makedirs(safe_dir, exist_ok=True)
            # Set permissions to 700 (user only)
            os.chmod(safe_dir, 0o700)
    else:
        # If sandbox mode is disabled and no directories specified, use defaults
        if not os.environ.get("SAFE_OUTPUT_DIRECTORIES"):
            # Use tempfile.gettempdir() instead of hardcoded /tmp
            temp_base = tempfile.gettempdir()
            var_temp = os.path.join(os.path.dirname(temp_base), "var", "tmp")
            if not os.path.exists(var_temp):
                var_temp = temp_base  # Fallback if /var/tmp doesn't exist

            default_dirs = f"{os.path.join(temp_base, 'extracted_images')}:{os.path.join(var_temp, 'extracted_images')}"
            os.environ["SAFE_OUTPUT_DIRECTORIES"] = default_dirs
            print(
                f"Sandbox mode disabled: Using default output directories: {default_dirs}"
            )

            # Create the directories
            for dir_path in default_dirs.split(":"):
                os.makedirs(dir_path, exist_ok=True)
                # Use 0o700 permissions for better security, even in non-sandbox mode
                os.chmod(dir_path, 0o700)

    # Process command-line arguments
    args = sys.argv[1:]

    # If sandbox mode is disabled and --allow-any-path is not in args, add it
    if not sandbox_mode and "--allow-any-path" not in args:
        print("Sandbox mode disabled: Adding --allow-any-path flag")
        args.append("--allow-any-path")

    # Add PORT from environment if specified and --port is not in args
    port = os.environ.get("PORT")
    if port and not any(arg.startswith("--port") for arg in args):
        args.extend(["--port", port])

    # Update sys.argv for the server_main function
    sys.argv = [sys.argv[0]] + args

    # Call the main function from standalone_server
    print(
        f"Starting document understanding MCP server with arguments: {' '.join(args)}"
    )
    server_main()


if __name__ == "__main__":
    cli_main()
