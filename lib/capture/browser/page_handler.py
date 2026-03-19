"""
Page Handler

Manages individual page operations including navigation, content capture,
and network monitoring within browser contexts.
"""

import asyncio
from typing import Optional, Dict, Any, List, Callable, TYPE_CHECKING
from datetime import datetime
from pathlib import Path

if TYPE_CHECKING:
    from playwright.async_api import Page, Response, Request

try:
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    PlaywrightTimeoutError = TimeoutError

from ..storage.models import PageCapture, NetworkRequest, CaptureSession


class PageHandler:
    """Handles page-level operations and network monitoring"""
    
    def __init__(self, page: "Page", session: CaptureSession):
        """Initialize page handler
        
        Args:
            page: Playwright page instance
            session: Capture session this page belongs to
        """
        self.page = page
        self.session = session
        self.network_requests: List[NetworkRequest] = []
        self.page_capture: Optional[PageCapture] = None
        self._request_counter = 0
        self._listeners_setup = False
    
    async def setup_network_monitoring(self) -> None:
        """Setup network request/response monitoring"""
        if self._listeners_setup:
            return
            
        self.page.on("request", self._on_request)
        self.page.on("response", self._on_response)
        self._listeners_setup = True
    
    async def navigate_and_capture(
        self, 
        url: str, 
        wait_for: str = "domcontentloaded",  # Changed default for faster loading
        timeout: int = 30000
    ) -> PageCapture:
        """Navigate to URL and capture page data
        
        Args:
            url: URL to navigate to
            wait_for: Wait condition ('load', 'domcontentloaded', 'networkidle')
            timeout: Timeout in milliseconds
            
        Returns:
            PageCapture with captured data
        """
        # Setup monitoring before navigation
        await self.setup_network_monitoring()
        
        # Create page capture record
        self.page_capture = PageCapture(
            session_id=self.session.session_id,
            sequence_number=self.session.current_capture_index,
            url=url,
            started_at=datetime.now()
        )
        
        try:
            # Navigate to the page
            print(f"   🔍 DEBUG: About to call page.goto('{url}')")
            print(f"   🔍 DEBUG: Page URL before goto: {self.page.url}")
            
            response = await self.page.goto(url, wait_until=wait_for, timeout=timeout)
            
            print(f"   🔍 DEBUG: page.goto() completed")
            print(f"   🔍 DEBUG: Response: {response}")
            
            # Update capture with response data
            if response:
                self.page_capture.final_url = response.url
                self.page_capture.title = await self.page.title()
                print(f"   ✅ Navigation successful to: {response.url}")
            else:
                print(f"   ⚠️ No response from page.goto()")
            
            # Capture page content
            await self._capture_page_content()
            
            # Mark as completed
            self.page_capture.completed_at = datetime.now()
            if self.page_capture.started_at:
                delta = self.page_capture.completed_at - self.page_capture.started_at
                self.page_capture.load_time_ms = int(delta.total_seconds() * 1000)
            
            # Update statistics
            self.page_capture.network_requests_count = len(self.network_requests)
            
        except Exception as e:
            print(f"   ❌ DEBUG: Exception during navigation: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            self.page_capture.errors_encountered.append(str(e))
            if not self.page_capture.completed_at:
                self.page_capture.completed_at = datetime.now()
        
        return self.page_capture
    
    async def _capture_page_content(self) -> None:
        """Capture page HTML content and metadata"""
        try:
            # Get page content
            html_content = await self.page.content()
            
            # Save HTML content to file if page_capture exists
            if self.page_capture:
                # Create a simple filename for the HTML content
                import os
                from pathlib import Path
                
                # Create captures directory if it doesn't exist
                captures_dir = Path("captures")
                captures_dir.mkdir(exist_ok=True)
                
                # Generate filename
                html_filename = f"capture_{self.page_capture.capture_id}.html"
                html_path = captures_dir / html_filename
                
                # Save HTML content to file
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                # Update the path in the capture object
                self.page_capture.final_html_path = str(html_path)
                
                # Detect potential API endpoints from network requests
                api_calls = [
                    req.url for req in self.network_requests 
                    if req.is_api_call
                ]
                self.page_capture.api_calls_detected = api_calls
                
        except Exception as e:
            if self.page_capture:
                self.page_capture.errors_encountered.append(f"Content capture error: {str(e)}")
    
    def _on_request(self, request: "Request") -> None:
        """Handle network request events"""
        self._request_counter += 1
        
        # Create network request record
        network_req = NetworkRequest(
            sequence_number=self._request_counter,
            url=request.url,
            method=request.method,
            headers=dict(request.headers),
            timestamp=datetime.now(),
            is_api_call=self._is_api_call(request.url, request.headers),
        )
        
        # Add request body if present
        try:
            post_data = request.post_data
            if post_data:
                network_req.body = post_data
        except Exception:
            pass  # Some requests may not have accessible post data
        
        self.network_requests.append(network_req)
    
    def _on_response(self, response: "Response") -> None:
        """Handle network response events"""
        # Find corresponding request
        matching_request = None
        for req in self.network_requests:
            if req.url == response.url and req.response_status is None:
                matching_request = req
                break
        
        if matching_request:
            # Update request with response data
            matching_request.response_status = response.status
            matching_request.response_headers = dict(response.headers)
            
            # Detect media content
            content_type = response.headers.get('content-type', '').lower()
            matching_request.is_media_content = any(
                media_type in content_type 
                for media_type in ['image/', 'video/', 'audio/']
            )
            
            # Try to capture response body for API calls (be careful with size)
            if matching_request.is_api_call and response.status == 200:
                try:
                    # Only capture small responses to avoid memory issues
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) < 1024 * 1024:  # 1MB limit
                        asyncio.create_task(self._capture_response_body(response, matching_request))
                except (ValueError, TypeError):
                    pass
    
    async def _capture_response_body(self, response: "Response", network_req: NetworkRequest) -> None:
        """Capture response body for API calls"""
        try:
            body = await response.text()
            network_req.response_body = body
        except Exception as e:
            # Don't fail the whole capture for response body issues
            pass
    
    def _is_api_call(self, url: str, headers: Dict[str, str]) -> bool:
        """Determine if a request is likely an API call"""
        # Check for common API indicators
        api_indicators = [
            '/api/', '/rest/', '/graphql', '/v1/', '/v2/', '/v3/',
            'application/json' in headers.get('content-type', '').lower(),
            'application/json' in headers.get('accept', '').lower(),
        ]
        
        return any(indicator in url.lower() if isinstance(indicator, str) and '/' in indicator 
                  else indicator for indicator in api_indicators)
    
    async def wait_for_condition(
        self, 
        condition: str, 
        timeout: int = 30000,
        **kwargs
    ) -> bool:
        """Wait for specific page conditions
        
        Args:
            condition: Type of condition to wait for
            timeout: Timeout in milliseconds
            **kwargs: Additional condition-specific arguments
            
        Returns:
            True if condition met, False if timeout
        """
        try:
            if condition == "selector":
                selector = kwargs.get("selector")
                if selector:
                    await self.page.wait_for_selector(selector, timeout=timeout)
                    return True
            elif condition == "function":
                js_function = kwargs.get("function")
                if js_function:
                    await self.page.wait_for_function(js_function, timeout=timeout)
                    return True
            elif condition == "load_state":
                state = kwargs.get("state", "networkidle")
                await self.page.wait_for_load_state(state, timeout=timeout)
                return True
            
            return False
            
        except Exception:
            return False
    
    async def take_screenshot(self, full_page: bool = True) -> Optional[bytes]:
        """Take a screenshot of the current page
        
        Args:
            full_page: Whether to capture full page or just viewport
            
        Returns:
            Screenshot data as bytes, None if failed
        """
        try:
            if not self.page:
                raise RuntimeError("Page is not available for screenshot")
            
            screenshot = await self.page.screenshot(full_page=full_page)
            return screenshot
        except Exception as e:
            # For integration tests, we want to see the actual error
            print(f"Screenshot failed: {type(e).__name__}: {e}")
            return None
    
    def get_network_summary(self) -> Dict[str, Any]:
        """Get summary of network activity
        
        Returns:
            Dictionary with network statistics
        """
        total_requests = len(self.network_requests)
        api_calls = [req for req in self.network_requests if req.is_api_call]
        media_requests = [req for req in self.network_requests if req.is_media_content]
        failed_requests = [req for req in self.network_requests if req.response_status and req.response_status >= 400]
        
        return {
            "total_requests": total_requests,
            "api_calls": len(api_calls),
            "media_requests": len(media_requests),
            "failed_requests": len(failed_requests),
            "unique_domains": len(set(req.url.split('/')[2] for req in self.network_requests if '/' in req.url)),
        }
