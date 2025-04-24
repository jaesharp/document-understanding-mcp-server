# Module for table extraction logic
import tabula
import pandas as pd
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from ..logging_config import get_logger
import subprocess  # nosec B404 # Reason: Subprocess needed for tabula Java process error handling.
from ..exceptions import PDFPasswordError, TableExtractionError

# Use TYPE_CHECKING to avoid circular import
if TYPE_CHECKING:
    from .extractor import PDFExtractor  # Relative import for type hint

logger = get_logger(__name__)


def _extract_tables_impl(
    extractor: "PDFExtractor",  # Use type hint
    pdf_path: str,
    pages_spec: Optional[str],
    password: Optional[str] = None,  # Added password argument
) -> List[Dict[str, Any]]:
    """
    Core implementation for extracting tables using Tabula.
    """
    log = extractor.log  # Use extractor's logger
    log.debug(
        f"Entering _extract_tables_impl for {pdf_path}, pages: {pages_spec or 'all'}"
    )

    if not extractor.check_file_exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # Standardize page spec for tabula (needs 'all' or specific numbers)
    tabula_pages = pages_spec if pages_spec else "all"

    try:
        # Call tabula-py, passing the password argument
        tables = tabula.read_pdf(
            pdf_path,
            pages=tabula_pages,
            multiple_tables=True,
            pandas_options={"header": None},  # Treat first row as data initially
            password=password,  # Pass password to tabula
        )

        if not tables:
            log.info(
                f"No tables found by Tabula in '{pdf_path}' for pages '{tabula_pages}'"
            )
            return []

        # Process extracted tables (which are pandas DataFrames)
        results = []
        for idx, df in enumerate(tables):
            # Simple conversion to list of lists
            # Consider more robust NaN handling or type conversion if needed
            table_data = [df.columns.values.tolist()] + df.values.tolist()
            # Clean data: replace NaN/None with empty strings for JSON compatibility
            cleaned_data = [
                [str(cell) if pd.notna(cell) else "" for cell in row]
                for row in table_data
            ]

            # Note: Tabula doesn't directly give page number per table if pages='all'
            # We might need to refine this if page association is critical
            # For now, we return a list without specific page numbers per table
            # Update: The Table model expects page_number and table_number.
            # Use idx for table_number and -1 for page_number when pages='all'.
            results.append(
                {
                    "table_number": idx,  # Renamed from table_index to match model/test
                    "page_number": -1,  # Page number unknown when pages='all'
                    "data": cleaned_data,
                }
            )

        log.info(f"Successfully extracted {len(results)} table(s) from '{pdf_path}'")
        return results

    # Handle specific tabula/Java errors if possible
    except subprocess.CalledProcessError as e:
        # This can happen if the Java process fails
        error_output = e.stderr.decode() if e.stderr else "No stderr"
        log.error(
            f"Tabula Java process failed for '{pdf_path}': {error_output}",
            exc_info=True,
        )
        # Check if it looks like a password error from Java output
        if "password" in error_output.lower():
            raise PDFPasswordError(
                f"PDF is likely password protected (Tabula error): {pdf_path}"
            ) from e
        raise TableExtractionError(
            f"Table extraction failed for PDF '{pdf_path}': Tabula subprocess error - {error_output}"
        ) from e
    except FileNotFoundError as e:
        # Catch if Java runtime itself isn't found
        if "java" in str(e).lower():
            log.error("Java runtime not found. tabula-py requires Java.", exc_info=True)
            raise TableExtractionError(
                "Table extraction requires Java runtime, which was not found."
            ) from e
        else:
            # Should be caught by initial check, but handle just in case
            raise e
    except Exception as e:
        # Catch other potential errors (e.g., tabula parsing issues, invalid PDF)
        # Check if the error message suggests a password issue
        err_str = str(e).lower()
        if "password" in err_str or "encrypted" in err_str:
            raise PDFPasswordError(
                f"Table extraction failed, likely due to password protection: {pdf_path}"
            ) from e

        log.error(f"Error extracting tables from '{pdf_path}': {e}", exc_info=True)
        raise TableExtractionError(
            f"Failed to extract tables from '{pdf_path}': {e}"
        ) from e
