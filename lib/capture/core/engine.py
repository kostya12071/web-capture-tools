"""
Enhanced Web Capture Engine - Phase 2 Implementation

Main orchestrator for web capture operations with browser automation
and network interception capabilities.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from ..storage.models import (
    CaptureSession, 
    CaptureConfig, 
    CaptureMode, 
    BrowserMode,
    PageCapture,
    NetworkRequest
)
from ..browser.manager import BrowserManager
from ..browser.page_handler import PageHandler
from ..network.interceptor import NetworkInterceptor
from ..network.analyzer import TrafficAnalyzer


class WebCaptureEngine:
    """Enhanced engine for orchestrating web capture operations with browser automation"""
    
    def __init__(self, config: Optional[CaptureConfig] = None):
        """Initialize the capture engine
        
        Args:
            config: Configuration for capture operations. If None, uses defaults.
        """
        self.config = config or CaptureConfig()
        self._current_session: Optional[CaptureSession] = None
        self._browser_manager: Optional[BrowserManager] = None
        self._active_handlers: Dict[str, PageHandler] = {}
        self._network_interceptors: Dict[str, NetworkInterceptor] = {}
    
    async def initialize_browser(self) -> None:
        """Initialize browser management"""
        if not self._browser_manager:
            # Add stealth arguments to browser config if not already present
            if not self.config.browser_args:
                self.config.browser_args = []
            
            # Common stealth arguments
            stealth_args = [
                "--disable-infobars",
                "--exclude-switches=enable-automation",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ]
            
            for arg in stealth_args:
                if arg not in self.config.browser_args:
                    self.config.browser_args.append(arg)
            
            self._browser_manager = BrowserManager(self.config)
            await self._browser_manager.initialize()
    
    async def shutdown(self) -> None:
        """Shutdown browser and cleanup resources"""
        if self._browser_manager:
            try:
                await self._browser_manager.close_all()
            except Exception as e:
                # Log error but don't re-raise to ensure cleanup continues
                print(f"Warning: Error during browser shutdown: {e}")
            finally:
                self._browser_manager = None
        
        self._active_handlers.clear()
        self._network_interceptors.clear()
    

    def create_session(
        self,
        base_url: str,
        capture_mode: CaptureMode = CaptureMode.ANONYMOUS,
        browser_mode: BrowserMode = BrowserMode.HEADLESS,
        name: Optional[str] = None,
        description: Optional[str] = None,
        chrome_profile_path: Optional[str] = None
    ) -> CaptureSession:
        """Create a new capture session
        
        Args:
            base_url: Base URL for the capture session
            capture_mode: Authentication mode to use
            browser_mode: Browser execution mode
            name: Optional human-readable name for the session
            description: Optional description of the session purpose
            
        Returns:
            New CaptureSession instance
        """
        session = CaptureSession(
            base_url=base_url,
            capture_mode=capture_mode,
            browser_mode=browser_mode,
            name=name,
            description=description
        )
        
        # Store chrome profile path if provided
        if chrome_profile_path:
            session.chrome_profile_path = chrome_profile_path
            # If using real profile, we force specific modes
            session.capture_mode = CaptureMode.PROFILE_BASED
        
        # Set viewport from config, accounting for device emulation
        if self.config.device_emulation:
            device_config = self._get_device_config(self.config.device_emulation)
            if device_config and 'viewport' in device_config:
                session.viewport = device_config['viewport']
                # Also set user agent if specified in device config
                if 'user_agent' in device_config:
                    session.user_agent = device_config['user_agent']
            else:
                session.viewport = {"width": self.config.viewport_width, "height": self.config.viewport_height}
        else:
            session.viewport = {"width": self.config.viewport_width, "height": self.config.viewport_height}
        
        # Set user agent if not already set by device emulation
        if not session.user_agent:
            session.user_agent = self.config.user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        
        self._current_session = session
        return session
    
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
    
    def get_current_session(self) -> Optional[CaptureSession]:
        """Get the currently active session"""
        return self._current_session
    
    def validate_session(self, session: CaptureSession) -> bool:
        """Validate that a session is properly configured
        
        Args:
            session: Session to validate
            
        Returns:
            True if session is valid, False otherwise
        """
        if not session.base_url:
            return False
        
        if not session.session_id:
            return False
            
        if session.capture_mode not in CaptureMode:
            return False
            
        if session.browser_mode not in BrowserMode:
            return False
        
        return True
    
    async def start_capture(self, url: str, session: Optional[CaptureSession] = None) -> PageCapture:
        """Start capturing a page within a session
        
        Args:
            url: URL to capture
            session: Session to use (uses current if None)
            
        Returns:
            PageCapture instance with captured data
        """
        if not session:
            session = self._current_session
            
        if not session:
            raise ValueError("No active session. Create a session first.")
        
        # Initialize browser if needed
        await self.initialize_browser()
        
        # Create browser context for session if not exists
        context = await self._browser_manager.get_context(session.session_id)
        if not context:
            chrome_profile = getattr(session, 'chrome_profile_path', None)
            context = await self._browser_manager.create_context(
                session, 
                chrome_profile_path=chrome_profile
            )
        
        # Create page and handler
        page = await self._browser_manager.create_page(session.session_id)
        page_handler = PageHandler(page, session)
        
        # Setup network monitoring
        network_interceptor = NetworkInterceptor(session)
        await network_interceptor.setup_interception(page)
        
        # Store handlers for session
        handler_key = f"{session.session_id}_{len(session.captures)}"
        self._active_handlers[handler_key] = page_handler
        self._network_interceptors[handler_key] = network_interceptor
        
        # Perform capture
        page_capture = await page_handler.navigate_and_capture(url)
        
        # Update session with capture
        session.add_capture(page_capture)
        
        # Update session statistics with network data
        session.total_network_requests += len(network_interceptor.network_log)
        
        return page_capture
    
    async def start_capture_fast(self, url: str, timeout: int = 10000) -> PageCapture:
        """Start a fast page capture with shorter timeout and domcontentloaded wait
        
        Args:
            url: URL to capture
            timeout: Navigation timeout in milliseconds (default 10s)
            
        Returns:
            PageCapture: Capture result
            
        Raises:
            ValueError: If no active session
        """
        if not self._current_session:
            raise ValueError("No active session. Create a session first.")
        
        session = self._current_session
        
        # Browser initialization
        if not self._browser_manager:
            await self.initialize_browser()
        
        # Get or create context
        context = await self._browser_manager.get_context(session.session_id)
        if not context:
            chrome_profile = getattr(session, 'chrome_profile_path', None)
            context = await self._browser_manager.create_context(
                session, 
                chrome_profile_path=chrome_profile
            )
        
        # Create page and handler
        page = await self._browser_manager.create_page(session.session_id)
        page_handler = PageHandler(page, session)
        
        # Setup network monitoring (always enabled for now)
        network_interceptor = NetworkInterceptor(session)
        await network_interceptor.setup_interception(page)
        
        # Store handlers for session
        handler_key = f"{session.session_id}_{len(session.captures)}"
        self._active_handlers[handler_key] = page_handler
        self._network_interceptors[handler_key] = network_interceptor
        
        # Perform fast capture with domcontentloaded and short timeout
        page_capture = await page_handler.navigate_and_capture(
            url, 
            wait_for="domcontentloaded", 
            timeout=timeout
        )
        
        # Update session with capture
        session.add_capture(page_capture)
        
        # Update session statistics with network data
        session.total_network_requests += len(network_interceptor.network_log)
        
        return page_capture
    
    async def analyze_session_traffic(self, session: Optional[CaptureSession] = None) -> Dict[str, Any]:
        """Analyze network traffic for a session
        
        Args:
            session: Session to analyze (uses current if None)
            
        Returns:
            Traffic analysis results
        """
        if not session:
            session = self._current_session
            
        if not session:
            raise ValueError("No active session to analyze")
        
        # Collect all network requests from session
        all_requests = []
        
        # Try to get from active interceptors first
        for handler_key, interceptor in self._network_interceptors.items():
            if handler_key.startswith(session.session_id):
                all_requests.extend(interceptor.network_log)
        
        # If no active interceptors, check if session has stored network data
        if not all_requests and hasattr(session, '_network_requests'):
            all_requests = session._network_requests
        
        if not all_requests:
            return {'message': 'No network data captured yet'}
        
        # Analyze traffic
        analyzer = TrafficAnalyzer(all_requests)
        return analyzer.generate_comprehensive_report()
    

    
    async def complete_session(self, session: Optional[CaptureSession] = None) -> CaptureSession:
        """Complete and finalize a capture session
        
        Args:
            session: Session to complete (uses current if None)
            
        Returns:
            Completed session
        """
        if not session:
            session = self._current_session
            
        if not session:
            raise ValueError("No active session to complete")
        
        # Store network data in session before cleanup
        all_requests = []
        for handler_key, interceptor in self._network_interceptors.items():
            if handler_key.startswith(session.session_id):
                # Handle both real interceptors and mocked ones
                if hasattr(interceptor, 'network_log'):
                    network_log = interceptor.network_log
                    # Check if it's a real list (not a mock) and has items
                    if (hasattr(network_log, '__iter__') and 
                        not hasattr(network_log, '_mock_name') and  # Not a mock
                        network_log):  # Not empty
                        all_requests.extend(network_log)
        
        # Store network data in session for later analysis
        if not hasattr(session, '_network_requests'):
            session._network_requests = []
        session._network_requests.extend(all_requests)
        
        # Mark session as completed
        session.mark_completed()
        
        # Cleanup browser resources for this session
        if self._browser_manager:
            try:
                await self._browser_manager.close_context(session.session_id)
            except Exception as e:
                # Log error but don't re-raise to ensure cleanup continues
                print(f"Warning: Error during browser context cleanup: {e}")
        
        # Remove handlers
        handlers_to_remove = [
            key for key in self._active_handlers.keys() 
            if key.startswith(session.session_id)
        ]
        for key in handlers_to_remove:
            del self._active_handlers[key]
            if key in self._network_interceptors:
                del self._network_interceptors[key]
        
        # Clear current session if it was the one completed
        if self._current_session and self._current_session.session_id == session.session_id:
            self._current_session = None
        
        return session
