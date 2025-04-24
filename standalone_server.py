#!/usr/bin/env python3
"""
Entry point for the Document Understanding MCP server.
Imports and runs the server logic from the src/document_understanding package.
"""

import asyncio
import sys
import os

if __name__ == "__main__":
    # --- Path Setup ---
    project_root = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.join(project_root, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    # --- Imports from Config and Server (after path setup) ---
    try:
        from document_understanding.standalone_config import (
            parse_arguments,
            perform_pre_startup_checks,
            setup_server_config,
            configure_server_module
        )
        from document_understanding import server # Import the server module itself
    except ImportError as e:
        print(f"Error: Could not import required modules from src. Ensure src/document_understanding exists.", file=sys.stderr)
        print(f"Import Error: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Argument Parsing & Pre-Checks ---
    args = parse_arguments()
    try:
        perform_pre_startup_checks(argv=sys.argv[1:]) # Pass args to check
    except ValueError as config_err:
        print(f"ERROR: {config_err}", file=sys.stderr)
        sys.exit(1)

    # --- Full Configuration Setup ---
    try:
        # Determine final capabilities and paths based on args and env
        capabilities, allow_path, base_path = setup_server_config(args, os.environ)

        # Apply the determined configuration to the server module globals
        configure_server_module(server, capabilities, allow_path, base_path)
    except (ValueError, RuntimeError) as setup_err:
        print(f"ERROR: Configuration setup failed: {setup_err}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error during configuration setup: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Run Main Server Logic --- #
    try:
        # Now call the main function from the configured server module
        asyncio.run(server.main())
    except KeyboardInterrupt:
        print("Server stopped by user.", file=sys.stderr)
    except Exception as e:
        print(f"Server encountered an unhandled error: {e}", file=sys.stderr)
        sys.exit(1)