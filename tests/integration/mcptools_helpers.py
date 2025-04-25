"""
Helper functions for MCPTools-based E2E testing.

This module provides utility functions for launching and controlling
the PDF extraction server as a subprocess, and for running MCPTools
commands against it.
"""

import os
import json
import asyncio
import sys
import pytest
from pathlib import Path

# --- Constants ---
PYTHON_EXE = sys.executable
PROJECT_ROOT = Path(__file__).parent.parent.parent
CLI_MODULE = "document_understanding.cli"
STANDALONE_SCRIPT = str(PROJECT_ROOT / "src" / "document_understanding" / "cli.py")
SRC_PATH = str(PROJECT_ROOT / "src")
MCPTOOLS_PATH = "/usr/local/bin/mcp"


async def launch_server_subprocess(base_path, log_file=None, env_overrides=None):
    """
    Launch server as subprocess with specific configuration.

    Args:
        base_path: Base path for PDF files
        log_file: Path to log file (optional)
        env_overrides: Dictionary of environment variables to override (optional)

    Returns:
        Process object for the server subprocess
    """
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)

    if log_file:
        env["DOCUMENT_UNDERSTANDING_LOG_FILE"] = str(log_file)

    # Set base path using the new environment variable name
    env["DOCUMENT_UNDERSTANDING_BASE_PATH"] = str(base_path)

    # Disable sandbox mode for testing to maintain existing behavior
    env["DOCUMENT_UNDERSTANDING_SANDBOX"] = "false"

    # Launch server process using the Python module
    cmd = [PYTHON_EXE, "-m", CLI_MODULE]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        env=env,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Store base path on process for access in other methods
    process._base_path = str(base_path)

    # Give the server a moment to start up
    await asyncio.sleep(2)

    return process


async def shutdown_server_subprocess(process):
    """
    Gracefully shut down server subprocess.

    Args:
        process: Process object for the server subprocess
    """
    if process and process.returncode is None:
        try:
            process.terminate()
            await asyncio.wait_for(process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()


async def run_mcp_command(
    command, args=None, pdf_path=None, server_process=None, debug=False
):
    """
    Run a command against the actual MCP server using the mcptools CLI.

    Args:
        command: The MCP command to run (e.g., "extract-pdf-metadata")
        args: Dictionary of arguments to pass to the command
        pdf_path: Path to the PDF file (if applicable)
        server_process: Server process object (not used in this implementation)
        debug: Whether to print debug information

    Returns:
        JSON response from the server
    """
    if args is None:
        args = {}

    # Build the mcptools arguments
    mcptools_args = ["call", "tool", command]

    # Add PDF path if provided
    if pdf_path:
        mcptools_args.append(f"--pdf-path={pdf_path}")

    # Add other arguments
    for key, value in args.items():
        if isinstance(value, bool):
            if value:
                mcptools_args.append(f"--{key}")
        elif isinstance(value, dict):
            mcptools_args.append(f"--{key}={json.dumps(value)}")
        else:
            mcptools_args.append(f"--{key}={value}")

    # Define the server command using the CLI module
    server_command = [
        PYTHON_EXE,
        "-m",
        CLI_MODULE,
        "--ignore-missing-dependencies=java_runtime,tesseract_ocr",
    ]

    # Construct the full mcptools command
    full_command = [MCPTOOLS_PATH, *mcptools_args, *server_command]

    # Set up environment variables
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": SRC_PATH,
            "PYTHONUNBUFFERED": "1",
            "DOCUMENT_UNDERSTANDING_ALLOW_NO_JAVA": "true",
            "DOCUMENT_UNDERSTANDING_ALLOW_NO_TESSERACT": "true",
            "DOCUMENT_UNDERSTANDING_SANDBOX": "false",  # Disable sandbox mode for testing
        }
    )

    # If we have a base path from server_process, use it
    if server_process and hasattr(server_process, "_base_path"):
        env["DOCUMENT_UNDERSTANDING_BASE_PATH"] = server_process._base_path

    # Print the command for debugging
    if debug:
        print(f"\nRunning command: {' '.join(full_command)}")

    # Run the command
    try:
        process = await asyncio.create_subprocess_exec(
            *full_command,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=PROJECT_ROOT,
        )

        stdout, stderr = await process.communicate()

        # Print stdout and stderr for debugging
        if debug:
            print(f"\nCommand stdout: {stdout.decode() if stdout else ''}")
            print(f"\nCommand stderr: {stderr.decode() if stderr else ''}")
            print(f"\nReturn code: {process.returncode}")

        if process.returncode != 0:
            # Try to parse stderr as JSON first (might contain error info)
            try:
                return stderr.decode()
            except:
                return json.dumps(
                    {
                        "status": "error",
                        "message": f"Command failed with exit code {process.returncode}: {stderr.decode()}",
                    }
                )

        return stdout.decode()
    except Exception as e:
        return json.dumps(
            {"status": "error", "message": f"Failed to execute command: {str(e)}"}
        )


import pytest
import tempfile
from tests.pdf_generators import create_text_pdf, create_image_pdf


@pytest.fixture(scope="function")
def create_test_env():
    """
    Create a test environment with test PDFs.

    Returns:
        Dictionary with test environment information
    """
    # Create a temporary directory for the test
    with tempfile.TemporaryDirectory() as tmp_dir:
        work_dir = Path(tmp_dir) / "server_test"
        work_dir.mkdir()
        log_dir = work_dir / "logs"
        log_dir.mkdir()
        log_file = log_dir / "server.log"

        # Create a test PDF
        pdf_path = work_dir / "test.pdf"
        create_text_pdf(str(pdf_path))

        # Create an image PDF
        img_pdf_path = work_dir / "image.pdf"
        create_image_pdf(str(img_pdf_path))

        # Return the test environment
        yield {
            "work_dir": work_dir,
            "log_file": log_file,
            "pdf_path": pdf_path,
            "img_pdf_path": img_pdf_path,
        }


async def parse_json_response(response, debug=False):
    """
    Parse a JSON response and handle errors gracefully.

    Args:
        response: JSON response string
        debug: Whether to print debug information

    Returns:
        Parsed JSON object
    """
    try:
        json_obj = json.loads(response)
        if debug:
            print(f"\nParsed JSON: {json_obj}")
        return json_obj
    except json.JSONDecodeError as e:
        if debug:
            print(f"\nFailed to parse JSON: {e}")
            print(f"\nRaw response: {response}")
        return {
            "status": "error",
            "message": f"Failed to parse JSON: {e}",
            "raw_response": response,
        }
