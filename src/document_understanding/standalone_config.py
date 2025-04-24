"""Utility functions for standalone_server.py setup and configuration."""

import argparse
import sys
import os
import shutil
from pathlib import Path
from typing import Dict, Callable, Any, Optional, List, Tuple

# Ensure src is in path for document_understanding imports
# This might be needed if functions here import other things from the package
SCRIPT_DIR_CONFIG = os.path.dirname(os.path.abspath(__file__))
SRC_PATH_CONFIG = os.path.abspath(os.path.join(SCRIPT_DIR_CONFIG, ".."))
if SRC_PATH_CONFIG not in sys.path:
    sys.path.insert(0, SRC_PATH_CONFIG)

from .logging_config import get_logger  # Import logger config

logger = get_logger("standalone_config")

# --- Capability Definitions & Checks (Keep these internal for now) ---


def _check_java_runtime() -> bool:
    """Check if Java runtime is available via JAVA_HOME or PATH."""
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        java_exe = Path(java_home) / "bin" / "java"
        if java_exe.is_file() and os.access(str(java_exe), os.X_OK):
            logger.info(f"Found java executable via JAVA_HOME: {java_exe}")
            return True
        else:
            logger.warning(
                f"JAVA_HOME set to '{java_home}', but '{java_exe}' not found or not executable."
            )

    java_path = shutil.which("java")
    if java_path:
        logger.info(f"Found java executable in PATH: {java_path}")
        return True

    logger.info("Java runtime not found via JAVA_HOME or PATH.")
    return False


def _check_tesseract() -> bool:
    """Check if Tesseract executable is available via TESSERACT_HOME or PATH."""
    tesseract_home = os.environ.get("TESSERACT_HOME")
    if tesseract_home:
        tesseract_exe_direct = Path(tesseract_home) / "tesseract"
        tesseract_exe_bin = Path(tesseract_home) / "bin" / "tesseract"
        tesseract_exe = None
        if tesseract_exe_direct.is_file() and os.access(
            str(tesseract_exe_direct), os.X_OK
        ):
            tesseract_exe = tesseract_exe_direct
        elif tesseract_exe_bin.is_file() and os.access(str(tesseract_exe_bin), os.X_OK):
            tesseract_exe = tesseract_exe_bin

        if tesseract_exe:
            logger.info(
                f"Found tesseract executable via TESSERACT_HOME: {tesseract_exe}"
            )
            return True
        else:
            logger.warning(
                f"TESSERACT_HOME set to '{tesseract_home}', but executable not found or not executable."
            )

    tesseract_path = shutil.which("tesseract")
    if tesseract_path:
        logger.info(f"Found tesseract executable in PATH: {tesseract_path}")
        return True

    logger.info("Tesseract executable not found via TESSERACT_HOME or PATH.")
    return False


# Capability definition structure
CAPABILITIES_CONFIG: Dict[str, Dict[str, Any]] = {
    "java_runtime": {
        "check_func": _check_java_runtime,  # Use internal prefixed version
        "error_msg": "Java Runtime Environment (JRE) is required for the 'extract-tables' tool.",
    },
    "tesseract_ocr": {
        "check_func": _check_tesseract,  # Use internal prefixed version
        "error_msg": "Tesseract OCR executable is required for OCR fallback.",
    },
    "experimental_features": {
        "check_func": None,
        "arg_flag": "--enable-experimental",
        "arg_help": "Enable experimental tools. Disabled by default.",
    },
    "search_functionality": {
        "check_func": None,
        "arg_flag": "--disable-search",
        "arg_help": "Disable the 'search-pdf-text' tool.",
    },
}


def parse_arguments(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Document Understanding MCP Server")
    parser.add_argument(
        "--allow-any-path",
        action="store_true",
        help="DANGER: Allow server to access paths outside DOCUMENT_UNDERSTANDING_BASE_PATH.",
    )
    parser.add_argument(
        "--ignore-missing-dependencies",
        type=str,
        default="",
        help="Comma-separated list of capabilities to ignore if their dependency check fails (e.g., java_runtime,tesseract_ocr). Allows server to start with reduced functionality.",
    )
    # Add flags based on CAPABILITIES_CONFIG
    for name, cap_info in CAPABILITIES_CONFIG.items():
        if cap_info.get("arg_flag"):
            action = "store_true"
            if name == "search_functionality":
                action = "store_true"  # Flag presence means disable

            parser.add_argument(
                cap_info["arg_flag"], action=action, help=cap_info["arg_help"]
            )

    args_to_parse = argv if argv is not None else sys.argv[1:]
    return parser.parse_args(args_to_parse)


# --- Pre-Startup Check ---
def perform_pre_startup_checks(
    argv: Optional[List[str]] = None, env: Optional[Dict[str, str]] = None
) -> None:
    """
    Performs critical checks before full server initialization (e.g., asyncio loop).
    Parses args and checks for immediate configuration conflicts.
    Raises ValueError on conflicts.
    """
    effective_env = env if env is not None else os.environ
    args = parse_arguments(argv=argv)  # Parse args using the existing function

    allow_any_path = args.allow_any_path
    base_path_env = effective_env.get("DOCUMENT_UNDERSTANDING_BASE_PATH")

    if allow_any_path and base_path_env:
        # This is the specific check we want to perform early
        raise ValueError(
            "Configuration Error: Cannot use --allow-any-path flag when "
            "DOCUMENT_UNDERSTANDING_BASE_PATH environment variable is also set. "
            "Please use only one method to control path access."
        )
    # No other checks needed here for now, keep it focused


# --- Full Configuration Setup ---
def setup_server_config(
    args: argparse.Namespace,
    env: Dict[str, str],
    # Inject dependencies
    check_java_func: Callable[[], bool] = _check_java_runtime,
    check_tesseract_func: Callable[[], bool] = _check_tesseract,
    isdir_func: Callable[[str], bool] = os.path.isdir,
    makedirs_func: Callable[..., None] = os.makedirs,
    abspath_func: Callable[[str], str] = os.path.abspath,
) -> Tuple[Dict[str, bool], bool, Optional[str]]:
    """
    Validates configuration, checks dependencies, and determines final settings.
    Uses injected functions for dependency checks and OS operations.
    Raises ValueError or RuntimeError on critical errors.
    """
    # --- Base Path Configuration & Validation ---
    allow_any_path = args.allow_any_path
    base_path_env = env.get("DOCUMENT_UNDERSTANDING_BASE_PATH")
    base_path_abs = None

    # The pre-startup check already handled the conflict case
    # if allow_any_path and base_path_env:
    #     raise ValueError("Cannot use --allow-any-path flag when DOCUMENT_UNDERSTANDING_BASE_PATH environment variable is also set.")

    if allow_any_path:
        logger.warning(
            "Server starting with --allow-any-path. Access is *not* restricted. Use with caution."
        )
    else:
        if not base_path_env:
            raise ValueError(
                "DOCUMENT_UNDERSTANDING_BASE_PATH environment variable not set. Define this path or use --allow-any-path (unsafe)."
            )
        base_path_abs = abspath_func(base_path_env)  # Use injected abspath
        if not isdir_func(base_path_abs):  # Use injected isdir
            raise ValueError(
                f"DOCUMENT_UNDERSTANDING_BASE_PATH '{base_path_abs}' is not a valid directory."
            )
        logger.info(f"Restricting file access to base path: {base_path_abs}")

    # --- Dependency Check & Capability Status ---
    capability_status: Dict[str, bool] = {}
    missing_required_deps = []
    ignored_dependencies = {
        dep.strip()
        for dep in args.ignore_missing_dependencies.split(",")
        if dep.strip()
    }
    logger.debug(f"Ignoring missing dependencies for: {ignored_dependencies}")

    # Use the injected check functions
    check_funcs = {
        "java_runtime": check_java_func,
        "tesseract_ocr": check_tesseract_func,
    }

    for name, cap_info in CAPABILITIES_CONFIG.items():
        present = False
        is_ignored = name in ignored_dependencies

        if name == "experimental_features":
            present = args.enable_experimental
            capability_status[name] = present
            if not present:
                logger.info(
                    f"Experimental features are disabled. Use {cap_info['arg_flag']} to enable."
                )
        elif name == "search_functionality":
            is_disabled = args.disable_search
            capability_status[name] = not is_disabled
            if is_disabled:
                logger.info(
                    f"Search functionality disabled via {cap_info['arg_flag']}."
                )
        elif name in check_funcs:
            check_func = check_funcs[name]
            present = check_func()  # Call the injected check function
            effective_status = present and not is_ignored
            capability_status[name] = effective_status
            if not present:
                if not is_ignored:
                    logger.error(
                        f"{cap_info['error_msg']} Dependency check failed for '{name}'."
                    )
                    missing_required_deps.append(name)
                else:
                    logger.warning(
                        f"Dependency check failed for '{name}' but ignored. Functionality disabled."
                    )
            elif is_ignored:
                logger.warning(
                    f"Dependency '{name}' present but ignored. Functionality disabled."
                )
                capability_status[name] = False  # Ensure disabled if ignored
        else:
            # Default for capabilities without specific checks (handled by flags above)
            pass  # Already handled by experimental/search flags

    if missing_required_deps:
        raise RuntimeError(
            f"Missing required dependencies: {', '.join(missing_required_deps)}. Please install or use --ignore-missing-dependencies."
        )

    # --- Ensure Log Directory Exists ---
    log_file_path = env.get("DOCUMENT_UNDERSTANDING_LOG_FILE")
    if log_file_path:
        try:
            log_dir = os.path.dirname(
                abspath_func(log_file_path)
            )  # Use injected abspath
            if log_dir:
                makedirs_func(log_dir, exist_ok=True)  # Use injected makedirs
                logger.info(f"Ensured log directory exists: {log_dir}")
        except Exception as e:
            # Use injected logger
            logger.warning(
                f"Could not create log directory {log_dir}: {e}. File logging might fail."
            )

    return capability_status, allow_any_path, base_path_abs


def configure_server_module(
    server_module: Any,
    caps: Dict[str, bool],
    allow_path: bool,
    base_path: Optional[str],
):
    """Configures the imported server module globals."""
    # Note: Path setup is now assumed to happen before this via standard imports
    logger.debug(f"Final capability status being set: {caps}")
    server_module.SERVER_CAPABILITIES = caps
    server_module.ALLOW_ANY_PATH = allow_path
    server_module.BASE_PATH = base_path
