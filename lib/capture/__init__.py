"""
Universal Web Capture Framework

A comprehensive framework for capturing web traffic, browser state, and content
for research and automation development purposes.
"""

__version__ = "0.2.0"
__author__ = "Web Downloader Project"

from .storage.models import (
    CaptureSession, 
    PageCapture, 
    NetworkRequest,
    CaptureConfig,
    SessionStatus,
    CaptureMode,
    BrowserMode
)
from .core.engine import WebCaptureEngine
from .browser.manager import BrowserManager
from .browser.page_handler import PageHandler
from .network.interceptor import NetworkInterceptor
from .network.analyzer import TrafficAnalyzer

__all__ = [
    "CaptureSession",
    "PageCapture", 
    "NetworkRequest",
    "CaptureConfig",
    "SessionStatus",
    "CaptureMode",
    "BrowserMode",
    "WebCaptureEngine",
    "BrowserManager",
    "PageHandler",
    "NetworkInterceptor",
    "TrafficAnalyzer"
]
