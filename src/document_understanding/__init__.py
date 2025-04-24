# This file makes src/document_understanding a Python package.
from . import server  # Import the server module
import asyncio


def main():
    """Main entry point for the package."""
    asyncio.run(server.main())


# Optionally expose other important items at package level
__all__ = ["main", "server"]
