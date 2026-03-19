"""
Browser Manager

Handles browser lifecycle, context creation, and configuration for different
capture modes (anonymous, profile-based, authenticated).
"""

import asyncio
from typing import Optional, Dict, Any, List, Union, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Page

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    # Handle gracefully for testing without Playwright
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None

from ..storage.models import CaptureConfig, CaptureMode, BrowserMode, CaptureSession


class BrowserManager:
    """Manages browser instances and contexts for web capture"""
    
    def __init__(self, config: CaptureConfig):
        """Initialize browser manager with configuration
        
        Args:
            config: Capture configuration settings
        """
        self.config = config
        self.playwright = None
        self.browser: Optional["Browser"] = None
        self.contexts: Dict[str, "BrowserContext"] = {}
        self.active_pages: Dict[str, "Page"] = {}
        self._is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize Playwright and browser instance"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not available. Install with: pip install playwright")
        if self._is_initialized:
            return
        self.playwright = await async_playwright().start()
        self.browser_type = getattr(self.playwright, self.config.browser_type)
        launch_options = {
            'headless': self.config.headless,
        }
        if self.config.browser_args:
            launch_options['args'] = self.config.browser_args
        self.browser = await self.browser_type.launch(**launch_options)
        self._is_initialized = True
    
    async def create_context(
        self, 
        session: CaptureSession, 
        chrome_profile_path: Optional[str] = None
    ) -> "BrowserContext":
        """Create a browser context for a capture session
        
        Args:
            session: Capture session requiring a browser context
            chrome_profile_path: Optional path to real Chrome user data directory
            
        Returns:
            Configured browser context
        """
        if not self._is_initialized:
            await self.initialize()
        
        context_options = {
            'viewport': session.viewport,
            'user_agent': session.user_agent or None,
        }
        
        # Handle device emulation
        if self.config.device_emulation:
            device_config = self._get_device_config(self.config.device_emulation)
            if device_config:
                context_options.update(device_config)
        
        # Configure based on capture mode
        if chrome_profile_path:
            # WARNING: Chrome prevents automation on the main User Data directory
            # We must create a SEPARATE automation profile and copy cookies
            print(f"   📂 Source Chrome Profile: {chrome_profile_path}")
            
            # Use the provided profile path
            automation_profile_dir = Path(chrome_profile_path)
            automation_profile_dir.mkdir(exist_ok=True)
            
            print(f"   🔧 Using automation profile: {automation_profile_dir}")
            
            # Check if profile already has cookies
            cookies_file = automation_profile_dir / "Default" / "Network" / "Cookies"
            if cookies_file.exists():
                print(f"   ✅ Found existing session - should be logged in")
            else:
                print(f"   ℹ️  No session found - you'll need to login first")
                print(f"   💡 To login: Open regular Chrome with this profile:")
                print(f"      chrome.exe --user-data-dir=\"{automation_profile_dir.absolute()}\"")
                print(f"      Login to your site, then close Chrome and run automation")
            
            # When using real profile, we must use channel="chrome"
            args = self.config.browser_args if self.config.browser_args else []
            filtered_args = [arg for arg in args if not arg.startswith("--user-data-dir")]
            
            try:
                context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=str(automation_profile_dir),
                    # channel="chrome",  # Removed to align with Peeks and fix pipe error
                    headless=self.config.headless,    # Respect config setting
                    args=filtered_args,
                    **context_options
                )
                
                # In persistent mode, context IS the browser object
                self.contexts[session.session_id] = context
                self.browser = context  # For persistent context, browser is the context
                
                print(f"   ✅ Automation browser launched")
                
            except Exception as e:
                print(f"   ❌ Failed to launch automation browser: {e}")
                raise
            
        elif session.capture_mode == CaptureMode.PROFILE_BASED:
            # Use persistent context for profile-based captures (isolated profile)
            profile_dir = Path(session.output_directory) / "profile"
            context = await self.browser_type.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=self.config.headless,
                args=self.config.browser_args if self.config.browser_args else None,
                **context_options
            )
            # In persistent mode, context IS the browser object
            self.contexts[session.session_id] = context
            self.browser = context.browser if hasattr(context, 'browser') else context
        else:
            # Use regular context for anonymous captures
            context = await self.browser.new_context(**context_options)
            self.contexts[session.session_id] = context
        return context
    
    def _get_device_config(self, device_name: str) -> Optional[Dict[str, Any]]:
        """Get device emulation configuration
        
        Args:
            device_name: Name of device to emulate (e.g., 'iphone', 'android')
            
        Returns:
            Device configuration dictionary or None if device not supported
        """
        device_configs = {
            'iphone': {
                'viewport': {'width': 375, 'height': 667},
                'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
                'device_scale_factor': 2,
                'is_mobile': True,
                'has_touch': True,
            },
            'iphone_pro': {
                'viewport': {'width': 393, 'height': 852},
                'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
                'device_scale_factor': 3,
                'is_mobile': True,
                'has_touch': True,
            },
            'android': {
                'viewport': {'width': 360, 'height': 640},
                'user_agent': 'Mozilla/5.0 (Linux; Android 11; SM-A205U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
                'device_scale_factor': 3,
                'is_mobile': True,
                'has_touch': True,
            }
        }
        
        return device_configs.get(device_name.lower())
    
    async def get_context(self, session_id: str) -> Optional["BrowserContext"]:
        """Get existing context for session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Browser context if exists, None otherwise
        """
        return self.contexts.get(session_id)
    
    async def create_page(self, session_id: str) -> "Page":
        """Create a new page in the session's context
        
        Args:
            session_id: Session identifier
            
        Returns:
            New page instance
        """
        context = self.contexts.get(session_id)
        if not context:
            raise ValueError(f"No context found for session {session_id}")
        
        # For persistent contexts, check if there's already a page open
        # (persistent contexts often start with a default page)
        existing_pages = context.pages
        if existing_pages and len(existing_pages) > 0:
            # Use the first existing page
            page = existing_pages[0]
            print(f"   📄 Using existing page in persistent context")
        else:
            # Create a new page
            page = await context.new_page()
            print(f"   📄 Created new page in context")
            
        self.active_pages[f"{session_id}_{len(self.active_pages)}"] = page
        
        return page
    
    async def close_context(self, session_id: str) -> None:
        """Close browser context for session
        
        Args:
            session_id: Session identifier
        """
        context = self.contexts.get(session_id)
        if context:
            await context.close()
            del self.contexts[session_id]
            
        # Clean up associated pages
        pages_to_remove = [
            page_id for page_id in self.active_pages.keys()
            if page_id.startswith(session_id)
        ]
        for page_id in pages_to_remove:
            del self.active_pages[page_id]
    
    async def close_all(self) -> None:
        """Close all contexts and browser"""
        # Close all contexts
        for session_id in list(self.contexts.keys()):
            await self.close_context(session_id)
        
        # Close browser
        if self.browser:
            await self.browser.close()
            
        # Stop playwright
        if self.playwright:
            await self.playwright.stop()
        
        self._is_initialized = False
    
    def is_initialized(self) -> bool:
        """Check if browser manager is initialized"""
        return self._is_initialized
    
    async def get_browser_info(self) -> Dict[str, Any]:
        """Get information about the current browser instance
        
        Returns:
            Dictionary with browser information
        """
        if not self.browser:
            return {}
        
        return {
            'browser_type': self.config.browser_type,
            'headless': self.config.headless,
            'contexts_count': len(self.contexts),
            'active_pages_count': len(self.active_pages),
            'version': await self.browser.version(),
        }
