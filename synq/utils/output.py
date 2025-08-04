"""Cross-platform output utilities for CLI commands."""

import sys

# Emoji mappings for Windows compatibility
EMOJI_MAP: dict[str, str] = {
    "✅": "[OK]",
    "❌": "[ERROR]",
    "📦": "[LOAD]",
    "📸": "[SNAP]",
    "🔍": "[SCAN]",
    "📁": "[DIR]",
    "⚙️": "[CONFIG]",
    "🏷️": "[TAG]",
    "🤖": "[AUTO]",
    "📝": "[GEN]",
    "⬆️": "[UP]",
    "⬇️": "[DOWN]",
    "🗄️": "[DB]",
    "🔄": "[SYNC]",
}


def safe_echo(text: str) -> str:
    """
    Convert Unicode emojis to ASCII-safe alternatives on Windows.

    This prevents 'charmap' codec errors on Windows systems where
    the console doesn't support Unicode emoji characters.
    """
    if sys.platform == "win32":
        # Replace emojis with ASCII alternatives on Windows
        for emoji, replacement in EMOJI_MAP.items():
            text = text.replace(emoji, replacement)

    return text


def format_success(message: str) -> str:
    """Format a success message with appropriate icon."""
    return safe_echo(f"✅ {message}")


def format_error(message: str) -> str:
    """Format an error message with appropriate icon."""
    return safe_echo(f"❌ {message}")


def format_info(message: str, icon: str = "ℹ️") -> str:
    """Format an info message with appropriate icon."""
    return safe_echo(f"{icon} {message}")
