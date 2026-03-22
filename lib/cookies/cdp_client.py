"""
CDP Client
==========

Chrome DevTools Protocol client for cookie extraction.
"""

import asyncio
from typing import Optional

import aiohttp


DEFAULT_CDP_PORT = 9222


class CDPError(Exception):
    """CDP protocol error."""
    pass


class CDPClient:
    """
    Async Chrome DevTools Protocol client for cookie extraction.
    
    Connects to Chrome via the CDP WebSocket interface and provides
    methods to retrieve cookies filtered by domain.
    
    Usage:
        async with CDPClient(port=9222) as cdp:
            cookies = await cdp.get_cookies("example.com")
            
    Or manual lifecycle:
        cdp = CDPClient(port=9222)
        await cdp.connect()
        cookies = await cdp.get_cookies("example.com")
        await cdp.close()
    
    Args:
        port: CDP remote debugging port.
    """
    
    def __init__(self, port: int = DEFAULT_CDP_PORT):
        self._port = port
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._cdp_id = 0
    
    async def __aenter__(self) -> "CDPClient":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
    
    async def connect(self) -> None:
        """
        Connect to Chrome CDP WebSocket endpoint.
        
        Fetches the webSocketDebuggerUrl from /json/version and opens a WS.
        
        Raises:
            CDPError: If connection fails.
        """
        self._session = aiohttp.ClientSession()
        
        try:
            # Get the browser WS debugger URL
            async with self._session.get(
                f"http://localhost:{self._port}/json/version"
            ) as resp:
                if resp.status != 200:
                    raise CDPError(f"CDP /json/version returned {resp.status}")
                data = await resp.json()
            
            ws_url = data.get("webSocketDebuggerUrl")
            if not ws_url:
                raise CDPError("No webSocketDebuggerUrl in CDP /json/version response")
            
            self._ws = await self._session.ws_connect(ws_url)
            
        except aiohttp.ClientError as e:
            await self.close()
            raise CDPError(f"Failed to connect to CDP: {e}") from e
    
    async def close(self) -> None:
        """Close the CDP connection and cleanup resources."""
        if self._ws:
            await self._ws.close()
            self._ws = None
        
        if self._session:
            await self._session.close()
            self._session = None
    
    async def _send_cdp(self, method: str, params: Optional[dict] = None) -> dict:
        """
        Send a CDP command and wait for the matching response.
        
        Args:
            method: CDP method name (e.g. "Storage.getCookies").
            params: Optional parameters dict.
            
        Returns:
            The CDP response result dict.
            
        Raises:
            CDPError: If the command fails or connection is closed.
        """
        if not self._ws:
            raise CDPError("Not connected to CDP")
        
        self._cdp_id += 1
        msg_id = self._cdp_id
        message = {"id": msg_id, "method": method}
        if params:
            message["params"] = params
        
        await self._ws.send_json(message)
        
        # Read messages until we get our response (skip events)
        while True:
            msg = await self._ws.receive()
            
            if msg.type == aiohttp.WSMsgType.TEXT:
                resp = msg.json()
                if resp.get("id") == msg_id:
                    if "error" in resp:
                        error = resp["error"]
                        raise CDPError(
                            f"CDP error for {method}: {error.get('message', error)}"
                        )
                    return resp.get("result", {})
            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                raise CDPError("CDP WebSocket connection closed")
    
    async def get_all_cookies(self) -> list[dict]:
        """
        Retrieve all cookies from Chrome via CDP Storage.getCookies.
        
        Returns:
            List of CDP cookie dicts (each has name, value, domain, etc.).
        """
        result = await self._send_cdp("Storage.getCookies")
        return result.get("cookies", [])
    
    async def get_cookies(
        self,
        domain: str,
        cookie_names: Optional[list[str]] = None,
    ) -> dict[str, str]:
        """
        Get cookies for a specific domain, optionally filtered by name.
        
        Args:
            domain: Domain to filter cookies (e.g., "example.com").
            cookie_names: Optional list of cookie names to extract.
                          If None, returns all cookies for the domain.
        
        Returns:
            Dict mapping cookie names to values.
        """
        all_cookies = await self.get_all_cookies()
        result: dict[str, str] = {}
        
        for cookie in all_cookies:
            cookie_domain = cookie.get("domain", "")
            cookie_name = cookie.get("name", "")
            
            # Check domain match (handle leading dot)
            if domain in cookie_domain or cookie_domain.lstrip(".") == domain:
                # If specific names requested, filter
                if cookie_names is None or cookie_name in cookie_names:
                    result[cookie_name] = cookie.get("value", "")
        
        return result
    
    async def get_cookies_with_mapping(
        self,
        domain: str,
        cookie_names: list[str],
        field_mapping: Optional[dict[str, str]] = None,
    ) -> dict[str, str]:
        """
        Get cookies with optional field name mapping.
        
        Args:
            domain: Domain to filter cookies.
            cookie_names: List of cookie names to extract.
            field_mapping: Optional dict mapping cookie names to output field names.
                           E.g., {"x-userid": "user_id"} maps cookie "x-userid"
                           to field "user_id" in the output.
        
        Returns:
            Dict mapping field names (or cookie names) to values.
        """
        cookies = await self.get_cookies(domain, cookie_names)
        
        if not field_mapping:
            return cookies
        
        result: dict[str, str] = {}
        for cookie_name, value in cookies.items():
            field_name = field_mapping.get(cookie_name, cookie_name)
            result[field_name] = value
        
        return result
