import sys
import warnings
from pathlib import Path

import nest_asyncio
from loguru import logger


def content_to_text(content) -> str:
    """Flatten str | list[str | dict] message content to plain text."""
    if isinstance(content, list):
        return "\n".join(
            item if isinstance(item, str) else item.get("text", "")
            for item in content
            if isinstance(item, (str, dict))
        )
    return str(content)


def setup_environment():
    """Set up the application environment.

    Configures warnings, async support, and logging.
    """

    # Suppress warnings
    warnings.filterwarnings("ignore")

    # Enable nested asyncio (required for Jupyter notebooks)
    nest_asyncio.apply()

    # Configure logger
    configure_logger()


def configure_logger(level: str = "INFO"):
    """Configure the Loguru logger.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
    )
    logger.add(
        "logs/medreport_{time}.log",
        rotation="500 MB",
        retention="10 days",
        level=level,
    )


def print_separator(title: str = "", width: int = 80):
    """Print a visual separator with optional title.

    Args:
        title: Optional title to display in the separator
        width: Width of the separator line
    """
    if title:
        padding = (width - len(title) - 2) // 2
        print(f"\n{'=' * padding} {title} {'=' * padding}\n")
    else:
        print(f"\n{'=' * width}\n")


def validate_file_exists(file_path: str) -> bool:
    """Check if a file exists.

    Args:
        file_path: Path to the file

    Returns:
        True if file exists, False otherwise
    """
    return Path(file_path).exists()


def ensure_directory(dir_path: str):
    """Ensure a directory exists, create if it doesn't.

    Args:
        dir_path: Path to the directory
    """
    Path(dir_path).mkdir(parents=True, exist_ok=True)
