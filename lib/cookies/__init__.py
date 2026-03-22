"""
Cookie Capture Module
====================

CDP-based cookie extraction with profile management.
"""

from .cdp_client import CDPClient, CDPError
from .browser_launcher import BrowserLauncher, find_chrome, is_chrome_running
from .profile_manager import ProfileManager
from .cli import main

__all__ = [
    "CDPClient",
    "CDPError",
    "BrowserLauncher",
    "find_chrome",
    "is_chrome_running",
    "ProfileManager",
    "main",
]
