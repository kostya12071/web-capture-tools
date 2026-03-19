"""
Browser Management Module

Handles browser automation, lifecycle management, and context creation
for different capture modes.
"""

from .manager import BrowserManager
from .page_handler import PageHandler

__all__ = [
    "BrowserManager",
    "PageHandler"
]
