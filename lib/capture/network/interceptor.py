"""
Network Interceptor

Advanced network request/response interception with filtering,
modification capabilities, and detailed traffic analysis.
"""

from typing import List, Dict, Any, Optional, Callable, Set, TYPE_CHECKING
from datetime import datetime
import re
import json
from urllib.parse import urlparse

if TYPE_CHECKING:
    from playwright.async_api import Page, Route, Request, Response

from ..storage.models import NetworkRequest, CaptureSession


class NetworkInterceptor:
    """Advanced network traffic interceptor and analyzer"""
    
    def __init__(self, session: CaptureSession):
        """Initialize network interceptor
        
        Args:
            session: Capture session for context
        """
        self.session = session
        self.network_log: List[NetworkRequest] = []
        self.blocked_patterns: Set[str] = set()
        self.intercept_patterns: Set[str] = set()
        self.request_counter = 0
        self._custom_handlers: Dict[str, Callable] = {}
        
        # Default patterns for common tracking/analytics
        self.default_block_patterns = {
            r'.*google-analytics\.com.*',
            r'.*googletagmanager\.com.*',
            r'.*analytics\.google\.com.*',
            r'.*stats\.g\.doubleclick\.net.*',
            r'.*www\.google\.co\.il.*',
            r'.*facebook\.com/tr.*',
            r'.*doubleclick\.net.*',
            r'.*clarity\.ms.*',
            r'.*scripts\.clarity\.ms.*',
            r'.*q\.clarity\.ms.*',
            r'.*c\.clarity\.ms.*',
            r'.*c\.bing\.com.*',
            r'.*fonts\.googleapis\.com.*',
            r'.*fonts\.gstatic\.com.*',
            r'.*unpkg\.com.*',
            r'.*cdn\.branch\.io.*',
            r'.*app\.link.*',
            r'.*api2\.branch\.io.*',
            r'.*stats\.riavera\.com.*',
            r'.*emoji-datasource.*',
            r'.*gtag/js.*',
            r'.*analytics\.js.*',
            r'.*googlesyndication\.com.*'
        }
    
    async def setup_interception(self, page: "Page") -> None:
        """Setup network interception on a page
        
        Args:
            page: Playwright page to monitor
        """
        # Setup route interception for blocking/modifying requests
        await page.route("**/*", self._route_handler)
        
        # Setup event listeners for detailed monitoring
        page.on("request", self._on_request)
        page.on("response", self._on_response)
        page.on("requestfailed", self._on_request_failed)
    
    async def _route_handler(self, route: "Route") -> None:
        """Handle route interception for request modification/blocking
        
        Args:
            route: Playwright route object
        """
        request = route.request
        url = request.url
        
        # Check if request should be blocked
        if self._should_block_request(url):
            await route.abort()
            return
        
        # Check for custom handlers
        for pattern, handler in self._custom_handlers.items():
            if re.match(pattern, url):
                await handler(route, request)
                return
        
        # Default: continue with request
        await route.continue_()
    
    def _should_block_request(self, url: str) -> bool:
        """Check if request should be blocked
        
        Args:
            url: Request URL
            
        Returns:
            True if request should be blocked
        """
        all_patterns = self.blocked_patterns.union(self.default_block_patterns)
        return any(re.match(pattern, url) for pattern in all_patterns)
    
    def _on_request(self, request: "Request") -> None:
        """Handle request events"""
        self.request_counter += 1
        
        # Create detailed network request record
        network_req = NetworkRequest(
            sequence_number=self.request_counter,
            url=request.url,
            method=request.method,
            headers=dict(request.headers),
            timestamp=datetime.now(),
            is_api_call=self._classify_api_call(request),
            is_media_content=self._classify_media_content(request),
        )
        
        # Capture request body for POST/PUT requests
        try:
            if request.method in ['POST', 'PUT', 'PATCH'] and request.post_data:
                network_req.body = request.post_data
        except Exception:
            pass
        
        # Add to network log
        self.network_log.append(network_req)
    
    def _on_response(self, response: "Response") -> None:
        """Handle response events"""
        # Find matching request
        request_record = self._find_matching_request(response.url)
        
        if request_record:
            # Update with response data
            request_record.response_status = response.status
            request_record.response_headers = dict(response.headers)
            request_record.response_size_bytes = self._get_content_length(response.headers)
            
            # Capture response body for API calls and HTML pages (with size limits)
            if (request_record.is_api_call or self._is_html_page(response)) and self._should_capture_response_body(response):
                # Use asyncio to capture body without blocking (if loop is available)
                import asyncio
                try:
                    asyncio.create_task(self._capture_response_body(response, request_record))
                except RuntimeError:
                    # No running event loop (e.g., in tests), skip async body capture
                    pass
    
    def _on_request_failed(self, request: "Request") -> None:
        """Handle failed request events"""
        request_record = self._find_matching_request(request.url)
        if request_record:
            request_record.response_status = -1  # Indicate failure
            request_record.response_headers = {"error": "Request failed"}
    
    def _find_matching_request(self, url: str) -> Optional[NetworkRequest]:
        """Find matching request record by URL"""
        # Find the most recent request with this URL that doesn't have a response yet
        for request_record in reversed(self.network_log):
            if request_record.url == url and request_record.response_status is None:
                return request_record
        return None
    
    def _classify_api_call(self, request: "Request") -> bool:
        """Classify if request is an API call"""
        url = request.url.lower()
        headers = request.headers
        
        # Content type indicators
        content_type = headers.get('content-type', '').lower()
        accept = headers.get('accept', '').lower()
        
        # If content-type is HTML, it's not an API call regardless of URL
        if 'text/html' in content_type:
            return False
        
        # Common API indicators - check both domain and path
        api_patterns = [
            r'.*api\..*',        # api.example.com
            r'.*/api/.*',        # example.com/api/
            r'.*/rest/.*',       # example.com/rest/
            r'.*/graphql.*',     # example.com/graphql
            r'.*/v\d+/.*',       # example.com/v1/
            # Enhanced patterns for common API endpoints
            r'.*/fact[s]?(\?.*)?$',  # /fact, /facts endpoints (with optional query params)
            r'.*/users?.*',      # /user, /users endpoints  
            r'.*/data/.*',       # /data/ endpoints (more specific)
            r'.*/json.*',        # endpoints with 'json' in name
            # HTTP testing/debugging endpoints (httpbin.org patterns)
            r'.*/basic-auth.*',  # /basic-auth endpoints
            r'.*/bearer.*',      # /bearer token endpoints  
            r'.*/headers.*',     # /headers endpoints
            r'.*/auth.*',        # generic auth endpoints
            r'.*/token.*',       # token endpoints
            # Common REST API endpoints
            r'.*/objects.*',     # /objects endpoints
            r'.*/items.*',       # /items endpoints
            r'.*/posts.*',       # /posts endpoints
        ]
        
        content_indicators = [
            'application/json' in content_type,
            'application/json' in accept,
            'application/xml' in content_type,
            'text/xml' in content_type,
        ]
        
        return (any(re.match(pattern, url) for pattern in api_patterns) or
                any(content_indicators))
    
    def _classify_media_content(self, request: "Request") -> bool:
        """Classify if request is for media content"""
        url = request.url.lower()
        
        media_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp',  # Images
            '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm',   # Video
            '.mp3', '.wav', '.ogg', '.m4a', '.aac',           # Audio
        }
        
        # Check URL extension
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        return any(path.endswith(ext) for ext in media_extensions)
    
    def _get_content_length(self, headers: Dict[str, str]) -> Optional[int]:
        """Extract content length from headers"""
        content_length = headers.get('content-length')
        if content_length:
            try:
                return int(content_length)
            except ValueError:
                pass
        return None
    
    def _should_capture_response_body(self, response: "Response") -> bool:
        """Determine if response body should be captured"""
        # Only capture successful responses
        if response.status >= 400:
            return False
        
        # Check content type
        content_type = response.headers.get('content-type', '').lower()
        capturable_types = [
            'application/json',
            'application/xml',
            'text/xml',
            'text/plain',
            'text/html'
        ]
        
        if not any(ct in content_type for ct in capturable_types):
            return False
        
        # Check size limits
        content_length = self._get_content_length(response.headers)
        if content_length and content_length > 1024 * 1024:  # 1MB limit
            return False
        
        return True
    
    async def _capture_response_body(self, response: "Response", request_record: NetworkRequest) -> None:
        """Capture response body safely"""
        try:
            body = await response.text()
            request_record.response_body = body
        except Exception:
            # Don't fail if body can't be captured
            pass
    
    def _is_html_page(self, response: "Response") -> bool:
        """Check if response is an HTML page"""
        content_type = response.headers.get('content-type', '').lower()
        return 'text/html' in content_type
    
    def add_block_pattern(self, pattern: str) -> None:
        """Add URL pattern to block list
        
        Args:
            pattern: Regex pattern for URLs to block
        """
        self.blocked_patterns.add(pattern)
    
    def remove_block_pattern(self, pattern: str) -> None:
        """Remove URL pattern from block list
        
        Args:
            pattern: Regex pattern to remove
        """
        self.blocked_patterns.discard(pattern)
    
    def add_custom_handler(self, pattern: str, handler: Callable) -> None:
        """Add custom request handler
        
        Args:
            pattern: Regex pattern for URLs to handle
            handler: Async function to handle matching routes
        """
        self._custom_handlers[pattern] = handler
    
    def get_api_endpoints(self) -> List[Dict[str, Any]]:
        """Get discovered API endpoints
        
        Returns:
            List of API endpoint information
        """
        api_requests = [req for req in self.network_log if req.is_api_call]
        
        # Group by endpoint pattern
        endpoints = {}
        for req in api_requests:
            # Extract base endpoint (group by domain for APIs)
            parsed = urlparse(req.url)
            endpoint_key = f"{parsed.scheme}://{parsed.netloc}"
            
            if endpoint_key not in endpoints:
                endpoints[endpoint_key] = {
                    'base_url': endpoint_key,
                    'methods': set(),
                    'call_count': 0,
                    'status_codes': set(),
                    'first_seen': req.timestamp,
                    'last_seen': req.timestamp
                }
            
            endpoint = endpoints[endpoint_key]
            endpoint['methods'].add(req.method)
            endpoint['call_count'] += 1
            if req.response_status:
                endpoint['status_codes'].add(req.response_status)
            endpoint['last_seen'] = max(endpoint['last_seen'], req.timestamp)
        
        # Convert sets to lists for JSON serialization
        for endpoint in endpoints.values():
            endpoint['methods'] = list(endpoint['methods'])
            endpoint['status_codes'] = list(endpoint['status_codes'])
        
        return list(endpoints.values())
    
    def get_traffic_summary(self) -> Dict[str, Any]:
        """Get comprehensive traffic summary
        
        Returns:
            Dictionary with traffic statistics
        """
        total_requests = len(self.network_log)
        api_calls = [req for req in self.network_log if req.is_api_call]
        media_requests = [req for req in self.network_log if req.is_media_content]
        failed_requests = [req for req in self.network_log if req.response_status and req.response_status >= 400]
        
        # Calculate data transfer
        total_bytes = sum(
            req.response_size_bytes or 0 
            for req in self.network_log 
            if req.response_size_bytes
        )
        
        # Get unique domains
        domains = set()
        for req in self.network_log:
            parsed = urlparse(req.url)
            if parsed.netloc:
                domains.add(parsed.netloc)
        
        return {
            'total_requests': total_requests,
            'api_calls': len(api_calls),
            'media_requests': len(media_requests),
            'failed_requests': len(failed_requests),
            'unique_domains': len(domains),
            'domains': list(domains),
            'total_bytes_transferred': total_bytes,
            'api_endpoints_discovered': len(self.get_api_endpoints()),
        }
