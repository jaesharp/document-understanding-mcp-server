# Module for page parsing logic

"""Function for parsing page specification strings."""

import re
from typing import List, Optional, Set


def _parse_pages_impl(pages_str: Optional[str], total_pages: int) -> List[int]:
    """
    Parses a user-provided page string (1-based indexing) into a sorted list
    of 0-based page indices.
    (Moved from PDFExtractor.parse_pages)

    Supports:
    - Comma-separated values (e.g., "1, 3, 5")
    - Ranges (e.g., "1-3", "5-7")
    - Negative indices (e.g., "-1" for last, "-2" for second last)
    - Combinations (e.g., "1, 3-5, -1")

    Args:
        pages_str: The string representation of pages to parse, or None/empty/whitespace for all pages.
        total_pages: The total number of pages in the PDF document.

    Returns:
        A sorted list of unique 0-based page indices.

    Raises:
        ValueError: If the page string format is invalid or specifies invalid pages.
    """
    # Treat None, empty string, or whitespace-only string as selecting all pages
    if not pages_str or pages_str.isspace():
        if total_pages > 0:
            return list(range(total_pages))
        else:
            return []  # No pages if total_pages is 0

    selected_indices: Set[int] = set()
    # 1. Split by comma first
    comma_parts = pages_str.strip().split(",")

    for item in comma_parts:
        item = item.strip()
        if not item:
            continue

        try:
            # 2. Check for range specifically using hyphen, allowing negatives
            match = re.fullmatch(r"(-?\d+)\s*-\s*(-?\d+)", item)
            if match:
                start_str, end_str = match.groups()
                start = int(start_str)
                end = int(end_str)

                # Convert 1-based to 0-based, handling negatives
                start_idx = (start - 1) if start > 0 else (total_pages + start)
                end_idx = (end - 1) if end > 0 else (total_pages + end)

                # Check bounds *after* conversion to 0-based index
                if not (0 <= start_idx < total_pages):
                    raise ValueError(
                        f"Start page '{start}' (index {start_idx}) is outside the valid range (1-{total_pages})"
                    )
                if not (0 <= end_idx < total_pages):
                    raise ValueError(
                        f"End page '{end}' (index {end_idx}) is outside the valid range (1-{total_pages})"
                    )

                # Ensure start <= end
                if start_idx > end_idx:
                    start_idx, end_idx = end_idx, start_idx

                selected_indices.update(range(start_idx, end_idx + 1))

            # 3. Handle single page number (must be only digits, possibly with leading -)
            else:
                # Ensure it looks like a number before trying int()
                if not re.fullmatch(r"-?\d+", item):
                    raise ValueError(f"Invalid page number format: '{item}'")

                page = int(item)
                # Convert 1-based to 0-based, handling negatives
                page_idx = (page - 1) if page > 0 else (total_pages + page)

                if not (0 <= page_idx < total_pages):
                    raise ValueError(
                        f"Page number '{page}' (index {page_idx}) is outside the valid range (1-{total_pages})"
                    )
                selected_indices.add(page_idx)

        except ValueError as e:
            # Re-raise with more context including the problematic item
            if f"'{item}'" not in str(e):
                raise ValueError(
                    f"Invalid page specification part: '{item}'. Error: {e}"
                )
            else:
                raise e  # Reraise our specific errors
        except Exception as e:
            raise ValueError(
                f"Unexpected error parsing page specification part: '{item}'. Error: {e}"
            )

    # Treat empty or whitespace-only input as selecting all pages handled at the start
    # If non-whitespace input resulted in no pages, raise error
    if not selected_indices and pages_str and pages_str.strip():
        raise ValueError("Page specification resulted in no valid pages.")

    return sorted(list(selected_indices))
