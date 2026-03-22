"""
Browser Launcher
===============

Chrome browser launching with CDP remote debugging support.
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import aiohttp


# Default Chrome paths by platform
DEFAULT_CHROME_PATHS = {
    "win32": [
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("LocalAppData", ""), "Google", "Chrome", "Application", "chrome.exe"),
    ],
    "darwin": [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    ],
    "linux": [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
    ],
}

DEFAULT_PROFILE_DIR = "automation_profile_chrome"
DEFAULT_CDP_PORT = 9222
CDP_CONNECT_TIMEOUT = 15  # seconds


def find_chrome(custom_path: Optional[str] = None) -> Optional[str]:
    """
    Find the Chrome executable path.
    
    Args:
        custom_path: Optional custom path to check first.
        
    Returns:
        Path to Chrome executable, or None if not found.
    """
    if custom_path:
        if Path(custom_path).exists():
            return custom_path
    
    # Get platform-specific candidates
    platform = sys.platform
    if platform.startswith("linux"):
        platform = "linux"
    
    candidates = DEFAULT_CHROME_PATHS.get(platform, [])
    
    for path in candidates:
        if path and Path(path).exists():
            return path
    
    return None


async def is_chrome_running(port: int = DEFAULT_CDP_PORT) -> bool:
    """
    Check if Chrome CDP is available on the specified port.
    
    Args:
        port: CDP port to check.
        
    Returns:
        True if CDP endpoint is reachable.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://localhost:{port}/json/version",
                timeout=aiohttp.ClientTimeout(total=2),
            ) as resp:
                return resp.status == 200
    except (aiohttp.ClientError, asyncio.TimeoutError, OSError):
        return False


class BrowserLauncher:
    """
    Launch and manage Chrome browser with CDP remote debugging.
    
    The browser is launched as a detached process so it survives
    script termination. Users can continue browsing normally while
    the CDP connection monitors cookies.
    
    Args:
        chrome_path: Path to Chrome executable (auto-detected if None).
        profile_dir: Chrome --user-data-dir path.
        port: CDP remote debugging port.
    """
    
    def __init__(
        self,
        chrome_path: Optional[str] = None,
        profile_dir: str = DEFAULT_PROFILE_DIR,
        port: int = DEFAULT_CDP_PORT,
    ):
        self._chrome_path = chrome_path or find_chrome()
        self._profile_dir = Path(profile_dir)
        self._port = port
        self._process: Optional[subprocess.Popen] = None
    
    @property
    def chrome_path(self) -> Optional[str]:
        """Return the Chrome executable path."""
        return self._chrome_path
    
    @property
    def port(self) -> int:
        """Return the CDP port."""
        return self._port
    
    def launch(self, url: str = "about:blank") -> subprocess.Popen:
        """
        Launch Chrome with CDP remote debugging enabled.
        
        The process is detached so Chrome survives script exit.
        
        Args:
            url: Initial URL to open.
            
        Returns:
            The subprocess.Popen object.
            
        Raises:
            FileNotFoundError: If Chrome executable not found.
        """
        if not self._chrome_path:
            raise FileNotFoundError(
                "Chrome not found. Install Chrome or specify path with --chrome"
            )
        
        chrome_path = Path(self._chrome_path)
        if not chrome_path.exists():
            raise FileNotFoundError(f"Chrome not found at: {chrome_path}")
        
        # Ensure profile directory exists
        profile_dir = self._profile_dir.resolve()
        profile_dir.mkdir(parents=True, exist_ok=True)
        
        args = [
            str(chrome_path),
            f"--user-data-dir={profile_dir}",
            f"--remote-debugging-port={self._port}",
            url,
        ]
        
        # Detach process on Windows so it survives script exit
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
        
        self._process = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )
        
        return self._process
    
    async def wait_for_cdp(self, timeout: int = CDP_CONNECT_TIMEOUT) -> bool:
        """
        Wait for Chrome CDP endpoint to become available.
        
        Args:
            timeout: Maximum seconds to wait.
            
        Returns:
            True if CDP is ready, False on timeout.
        """
        for _ in range(timeout * 2):  # Check every 0.5s
            if await is_chrome_running(self._port):
                return True
            await asyncio.sleep(0.5)
        return False
    
    async def launch_and_wait(self, url: str = "about:blank", timeout: int = CDP_CONNECT_TIMEOUT) -> bool:
        """
        Launch Chrome and wait for CDP to be ready.
        
        Args:
            url: Initial URL to open.
            timeout: Maximum seconds to wait for CDP.
            
        Returns:
            True if Chrome launched and CDP is ready.
            
        Raises:
            FileNotFoundError: If Chrome executable not found.
        """
        self.launch(url)
        return await self.wait_for_cdp(timeout)
    
    def close(self) -> None:
        """
        Terminate the Chrome process if it was launched by this instance.
        
        Note: This will close all Chrome windows using the profile.
        """
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except (subprocess.TimeoutExpired, OSError):
                try:
                    self._process.kill()
                except OSError:
                    pass
            self._process = None
