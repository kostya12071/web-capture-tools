"""
Traffic Analyzer

Analyzes captured network traffic to identify patterns, extract insights,
and classify different types of network activity.
"""

from typing import List, Dict, Any, Set, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from urllib.parse import urlparse
import re
import json

from ..storage.models import NetworkRequest


class TrafficAnalyzer:
    """Analyzes network traffic patterns and extracts insights"""
    
    def __init__(self, network_requests: List[NetworkRequest]):
        """Initialize traffic analyzer
        
        Args:
            network_requests: List of captured network requests
        """
        self.requests = network_requests
        self._analysis_cache: Dict[str, Any] = {}
    
    def analyze_api_patterns(self) -> Dict[str, Any]:
        """Analyze API usage patterns
        
        Returns:
            Dictionary with API analysis results
        """
        if 'api_patterns' in self._analysis_cache:
            return self._analysis_cache['api_patterns']
        
        api_requests = [req for req in self.requests if req.is_api_call]
        
        if not api_requests:
            return {'total_api_calls': 0, 'endpoints': [], 'patterns': []}
        
        # Group by endpoint pattern
        endpoints = defaultdict(list)
        for req in api_requests:
            parsed = urlparse(req.url)
            # Create endpoint pattern (domain + first 2 path segments)
            path_parts = [p for p in parsed.path.split('/') if p]
            endpoint_pattern = f"{parsed.netloc}/{'/'.join(path_parts[:2])}" if path_parts else parsed.netloc
            endpoints[endpoint_pattern].append(req)
        
        # Analyze each endpoint
        endpoint_analysis = []
        for pattern, reqs in endpoints.items():
            methods = Counter(req.method for req in reqs)
            status_codes = Counter(req.response_status for req in reqs if req.response_status)
            
            # Calculate timing statistics
            response_times = [
                (req.response_timestamp - req.timestamp).total_seconds() * 1000
                for req in reqs 
                if req.response_timestamp and req.timestamp
            ]
            
            endpoint_data = {
                'pattern': pattern,
                'total_calls': len(reqs),
                'methods': dict(methods),
                'status_codes': dict(status_codes),
                'avg_response_time_ms': sum(response_times) / len(response_times) if response_times else 0,
                'first_call': min(req.timestamp for req in reqs),
                'last_call': max(req.timestamp for req in reqs)
            }
            endpoint_analysis.append(endpoint_data)
        
        # Identify common patterns
        patterns = self._identify_api_patterns(api_requests)
        
        result = {
            'total_api_calls': len(api_requests),
            'unique_endpoints': len(endpoints),
            'endpoints': endpoint_analysis,
            'patterns': patterns
        }
        
        self._analysis_cache['api_patterns'] = result
        return result
    
    def analyze_authentication_flows(self) -> Dict[str, Any]:
        """Analyze authentication-related requests
        
        Returns:
            Dictionary with authentication flow analysis
        """
        if 'auth_flows' in self._analysis_cache:
            return self._analysis_cache['auth_flows']
        
        # Common authentication indicators
        auth_indicators = {
            'login_urls': [r'.*login.*', r'.*signin.*', r'.*auth.*'],
            'token_headers': ['authorization', 'x-auth-token', 'x-api-key'],
            'session_cookies': ['sessionid', 'session', 'token', 'jwt']
        }
        
        auth_requests = []
        for req in self.requests:
            is_auth = False
            
            # Check URL patterns
            for pattern in auth_indicators['login_urls']:
                if re.match(pattern, req.url.lower()):
                    is_auth = True
                    break
            
            # Check headers
            if not is_auth:
                for header in auth_indicators['token_headers']:
                    if header in req.headers:
                        is_auth = True
                        break
            
            if is_auth:
                auth_requests.append(req)
        
        # Analyze authentication sequence
        auth_sequence = self._analyze_auth_sequence(auth_requests)
        
        result = {
            'auth_requests_count': len(auth_requests),
            'auth_sequence': auth_sequence,
            'potential_tokens': self._extract_potential_tokens(auth_requests)
        }
        
        self._analysis_cache['auth_flows'] = result
        return result
    
    def analyze_data_transfer(self) -> Dict[str, Any]:
        """Analyze data transfer patterns
        
        Returns:
            Dictionary with data transfer analysis
        """
        if 'data_transfer' in self._analysis_cache:
            return self._analysis_cache['data_transfer']
        
        # Calculate transfer statistics
        total_requests = len(self.requests)
        requests_with_size = [req for req in self.requests if req.response_size_bytes]
        
        if not requests_with_size:
            return {'total_bytes': 0, 'average_response_size': 0, 'largest_responses': []}
        
        total_bytes = sum(req.response_size_bytes for req in requests_with_size)
        avg_size = total_bytes / len(requests_with_size)
        
        # Find largest responses
        largest_responses = sorted(
            requests_with_size, 
            key=lambda r: r.response_size_bytes, 
            reverse=True
        )[:10]
        
        # Group by content type
        content_types = defaultdict(list)
        for req in requests_with_size:
            content_type = req.response_headers.get('content-type', 'unknown').split(';')[0]
            content_types[content_type].append(req.response_size_bytes)
        
        content_type_stats = {}
        for ct, sizes in content_types.items():
            content_type_stats[ct] = {
                'count': len(sizes),
                'total_bytes': sum(sizes),
                'avg_bytes': sum(sizes) / len(sizes)
            }
        
        result = {
            'total_bytes': total_bytes,
            'total_requests': total_requests,
            'requests_with_size': len(requests_with_size),
            'average_response_size': avg_size,
            'largest_responses': [
                {
                    'url': req.url,
                    'size_bytes': req.response_size_bytes,
                    'content_type': req.response_headers.get('content-type', 'unknown')
                }
                for req in largest_responses
            ],
            'content_type_breakdown': content_type_stats
        }
        
        self._analysis_cache['data_transfer'] = result
        return result
    
    def analyze_timing_patterns(self) -> Dict[str, Any]:
        """Analyze request timing patterns
        
        Returns:
            Dictionary with timing analysis
        """
        if 'timing_patterns' in self._analysis_cache:
            return self._analysis_cache['timing_patterns']
        
        # Calculate request intervals
        sorted_requests = sorted(self.requests, key=lambda r: r.timestamp)
        intervals = []
        
        for i in range(1, len(sorted_requests)):
            interval = (sorted_requests[i].timestamp - sorted_requests[i-1].timestamp).total_seconds()
            intervals.append(interval)
        
        # Detect request bursts (clusters of requests in short time)
        bursts = self._detect_request_bursts(sorted_requests)
        
        # Calculate response times for completed requests
        response_times = []
        for req in self.requests:
            if req.response_timestamp and req.timestamp:
                rt = (req.response_timestamp - req.timestamp).total_seconds() * 1000
                response_times.append(rt)
        
        result = {
            'total_duration_seconds': (
                (sorted_requests[-1].timestamp - sorted_requests[0].timestamp).total_seconds()
                if len(sorted_requests) > 1 else 0
            ),
            'average_request_interval': sum(intervals) / len(intervals) if intervals else 0,
            'request_bursts': bursts,
            'response_time_stats': {
                'count': len(response_times),
                'avg_ms': sum(response_times) / len(response_times) if response_times else 0,
                'min_ms': min(response_times) if response_times else 0,
                'max_ms': max(response_times) if response_times else 0
            }
        }
        
        self._analysis_cache['timing_patterns'] = result
        return result
    
    def identify_tracking_requests(self) -> Dict[str, Any]:
        """Identify analytics and tracking requests
        
        Returns:
            Dictionary with tracking analysis
        """
        # Common tracking domains and patterns
        tracking_patterns = [
            r'.*google-analytics\.com.*',
            r'.*googletagmanager\.com.*',
            r'.*facebook\.com/tr.*',
            r'.*doubleclick\.net.*',
            r'.*googlesyndication\.com.*',
            r'.*amazon-adsystem\.com.*',
            r'.*twitter\.com/i/adsct.*',
            r'.*linkedin\.com/px.*',
            r'.*hotjar\.com.*',
            r'.*mixpanel\.com.*'
        ]
        
        tracking_requests = []
        for req in self.requests:
            for pattern in tracking_patterns:
                if re.match(pattern, req.url.lower()):
                    tracking_requests.append({
                        'url': req.url,
                        'method': req.method,
                        'timestamp': req.timestamp,
                        'tracking_type': self._classify_tracking_type(req.url)
                    })
                    break
        
        # Group by tracking type
        tracking_types = defaultdict(int)
        for req in tracking_requests:
            tracking_types[req['tracking_type']] += 1
        
        return {
            'total_tracking_requests': len(tracking_requests),
            'tracking_requests': tracking_requests,
            'tracking_types': dict(tracking_types)
        }
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive traffic analysis report
        
        Returns:
            Complete analysis report
        """
        return {
            'summary': {
                'total_requests': len(self.requests),
                'analysis_timestamp': datetime.now(),
                'time_span': self._get_time_span()
            },
            'api_patterns': self.analyze_api_patterns(),
            'authentication_flows': self.analyze_authentication_flows(),
            'data_transfer': self.analyze_data_transfer(),
            'timing_patterns': self.analyze_timing_patterns(),
            'tracking_analysis': self.identify_tracking_requests()
        }
    
    def _identify_api_patterns(self, api_requests: List[NetworkRequest]) -> List[Dict[str, Any]]:
        """Identify common API patterns"""
        patterns = []
        
        # Pattern 1: Pagination
        pagination_indicators = ['page=', 'offset=', 'limit=', 'cursor=']
        pagination_requests = [
            req for req in api_requests 
            if any(indicator in req.url for indicator in pagination_indicators)
        ]
        
        if pagination_requests:
            patterns.append({
                'type': 'pagination',
                'description': 'API supports pagination',
                'evidence_count': len(pagination_requests),
                'example_urls': [req.url for req in pagination_requests[:3]]
            })
        
        # Pattern 2: CRUD operations
        crud_methods = {'GET', 'POST', 'PUT', 'DELETE', 'PATCH'}
        endpoints_with_crud = defaultdict(set)
        
        for req in api_requests:
            if req.method in crud_methods:
                parsed = urlparse(req.url)
                base_endpoint = f"{parsed.netloc}{parsed.path.split('?')[0]}"
                endpoints_with_crud[base_endpoint].add(req.method)
        
        full_crud_endpoints = [
            endpoint for endpoint, methods in endpoints_with_crud.items()
            if len(methods.intersection({'GET', 'POST', 'PUT', 'DELETE'})) >= 3
        ]
        
        if full_crud_endpoints:
            patterns.append({
                'type': 'crud_operations',
                'description': 'RESTful CRUD operations detected',
                'evidence_count': len(full_crud_endpoints),
                'example_endpoints': full_crud_endpoints[:3]
            })
        
        return patterns
    
    def _analyze_auth_sequence(self, auth_requests: List[NetworkRequest]) -> List[Dict[str, Any]]:
        """Analyze authentication sequence"""
        if not auth_requests:
            return []
        
        # Sort by timestamp
        sorted_auth = sorted(auth_requests, key=lambda r: r.timestamp)
        
        sequence = []
        for i, req in enumerate(sorted_auth):
            step = {
                'step': i + 1,
                'url': req.url,
                'method': req.method,
                'timestamp': req.timestamp,
                'status_code': req.response_status,
                'has_auth_headers': any(
                    header.lower() in ['authorization', 'x-auth-token', 'x-api-key']
                    for header in req.headers.keys()
                )
            }
            sequence.append(step)
        
        return sequence
    
    def _extract_potential_tokens(self, auth_requests: List[NetworkRequest]) -> List[str]:
        """Extract potential authentication tokens"""
        tokens = set()
        
        for req in auth_requests:
            # Check headers
            for header_name, header_value in req.headers.items():
                if header_name.lower() in ['authorization', 'x-auth-token', 'x-api-key']:
                    tokens.add(f"{header_name}: {header_value[:20]}...")
            
            # Check response bodies for tokens
            if req.response_body:
                try:
                    if req.response_body.startswith('{'):
                        data = json.loads(req.response_body)
                        for key in ['token', 'access_token', 'jwt', 'api_key']:
                            if key in data:
                                tokens.add(f"Response {key}: {str(data[key])[:20]}...")
                except (json.JSONDecodeError, AttributeError):
                    pass
        
        return list(tokens)
    
    def _detect_request_bursts(self, sorted_requests: List[NetworkRequest]) -> List[Dict[str, Any]]:
        """Detect bursts of requests in short time periods"""
        bursts = []
        
        if len(sorted_requests) < 3:
            return bursts
        
        burst_threshold = 1.0  # seconds
        min_burst_size = 3
        
        current_burst = [sorted_requests[0]]
        
        for i in range(1, len(sorted_requests)):
            time_diff = (sorted_requests[i].timestamp - current_burst[-1].timestamp).total_seconds()
            
            if time_diff <= burst_threshold:
                current_burst.append(sorted_requests[i])
            else:
                # End of burst
                if len(current_burst) >= min_burst_size:
                    bursts.append({
                        'start_time': current_burst[0].timestamp,
                        'end_time': current_burst[-1].timestamp,
                        'request_count': len(current_burst),
                        'duration_seconds': (current_burst[-1].timestamp - current_burst[0].timestamp).total_seconds()
                    })
                current_burst = [sorted_requests[i]]
        
        # Check final burst
        if len(current_burst) >= min_burst_size:
            bursts.append({
                'start_time': current_burst[0].timestamp,
                'end_time': current_burst[-1].timestamp,
                'request_count': len(current_burst),
                'duration_seconds': (current_burst[-1].timestamp - current_burst[0].timestamp).total_seconds()
            })
        
        return bursts
    
    def _classify_tracking_type(self, url: str) -> str:
        """Classify type of tracking request"""
        url_lower = url.lower()
        
        if 'google-analytics' in url_lower or 'googletagmanager' in url_lower:
            return 'Google Analytics'
        elif 'facebook.com/tr' in url_lower:
            return 'Facebook Pixel'
        elif 'doubleclick' in url_lower or 'googlesyndication' in url_lower:
            return 'Ad Network'
        elif 'hotjar' in url_lower:
            return 'User Behavior'
        elif 'mixpanel' in url_lower:
            return 'Product Analytics'
        else:
            return 'Other Tracking'
    
    def _get_time_span(self) -> Dict[str, Any]:
        """Get time span of captured requests"""
        if not self.requests:
            return {'start': None, 'end': None, 'duration_seconds': 0}
        
        timestamps = [req.timestamp for req in self.requests]
        start_time = min(timestamps)
        end_time = max(timestamps)
        
        return {
            'start': start_time,
            'end': end_time,
            'duration_seconds': (end_time - start_time).total_seconds()
        }
