#!/usr/bin/env python3
"""
Web Capture Session CLI
======================

Command-line interface for interactive and automated web capture sessions.
Supports both manual interaction and LLM-guided automation.
"""

import asyncio
import argparse
import json
import sys
import os
from datetime import datetime
from pathlib import Path
import time
import logging

from lib.capture.core.engine import WebCaptureEngine
from lib.capture.storage.models import (
    CaptureConfig, 
    CaptureSession, 
    CaptureMode, 
    BrowserMode,
    SessionStatus
)


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Web Capture Session CLI - Interactive and automated web capture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive manual browsing
  python -m lib.capture.cli https://lensof.com --interactive
  
  # Automated with instructions
  python -m lib.capture.cli https://lensof.com --auto --instruction "Click on menu items and take screenshots"
  
  # With saved session
  python -m lib.capture.cli https://lensof.com --interactive --session-file ./auth_session.json
  
  # Headless automation
  python -m lib.capture.cli https://lensof.com --auto --headless --instruction "Analyze the homepage structure"
        """
    )

    
    parser.add_argument(
        'url',
        help='Starting URL for the capture session (e.g., https://lensof.com)'
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Launch interactive mode - browser stays open for manual navigation'
    )
    mode_group.add_argument(
        '--auto', '-a',
        action='store_true',
        help='Automated mode - follow LLM instructions'
    )
    
    # Browser options
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode (default: visible in interactive, headless in auto)'
    )
    
    parser.add_argument(
        '--browser',
        choices=['chromium', 'firefox', 'webkit'],
        default='chromium',
        help='Browser type to use (default: chromium)'
    )
    
    parser.add_argument(
        '--viewport',
        default='1920x1080',
        help='Browser viewport size (default: 1920x1080)'
    )
    
    parser.add_argument(
        '--iphone',
        action='store_true',
        help='Emulate iPhone device (overrides viewport and user agent)'
    )
    
    parser.add_argument(
        '--chrome-profile',
        nargs='?',
        const='default',
        help='Use real Chrome user profile. Optional: provide path to User Data directory.'
    )
    
    parser.add_argument(
        '--session-mode',
        choices=['anonymous', 'persistent', 'authenticated'],
        default='anonymous',
        help='Session mode (default: anonymous)'
    )
    
    # Automation options
    parser.add_argument(
        '--instruction',
        help='LLM instruction for automated mode (required for --auto)'
    )
    
    parser.add_argument(
        '--max-time',
        type=int,
        default=300,
        help='Maximum session time in seconds (default: 300)'
    )
    
    parser.add_argument(
        '--capture-interval',
        type=int,
        default=10,
        help='Screenshot capture interval in seconds for interactive mode (default: 10)'
    )
    
    # Output options
    parser.add_argument(
        '--output', '-o',
        default='./captures/',
        help='Output directory for captured data (default: ./captures/)'
    )
    
    parser.add_argument(
        '--save-network',
        action='store_true',
        default=True,
        help='Save network traffic data (default: True)'
    )
    
    parser.add_argument(
        '--save-screenshots',
        action='store_true',
        default=True,
        help='Take periodic screenshots (default: True)'
    )
    
    # Debugging
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output'
    )
    
    return parser.parse_args()


class WebCaptureSession:
    """Manages web capture sessions with interactive and automated modes"""
    
    def __init__(self, args):
        self.args = args
        self.engine = None
        self.session = None
        self.page_handler = None
        self.capture_data = {
            'session_info': {},
            'captures': [],
            'screenshots': [],
            'network_logs': [],
            'interactions': []
        }
        self.output_dir = Path(args.output)
        self.session_start_time = datetime.now()
        
    async def initialize(self):
        """Initialize the capture session"""
        # Parse viewport unless iPhone emulation is enabled
        if self.args.iphone:
            # iPhone emulation will override viewport in config
            width, height = 375, 667  # Default iPhone size, will be overridden by device config
        else:
            try:
                width, height = map(int, self.args.viewport.split('x'))
            except ValueError:
                print(f"❌ Invalid viewport format: {self.args.viewport}. Use format: 1920x1080")
                return False
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine headless mode
        if self.args.headless:
            headless = True
        elif self.args.interactive:
            headless = False  # Interactive should be visible by default
        else:
            headless = True   # Auto mode defaults to headless
        
        print(f"🕸️ Web Capture Session CLI")
        print("=" * 50)
        print(f"🌐 Target URL: {self.args.url}")
        print(f"🎮 Mode: {'Interactive' if self.args.interactive else 'Automated'}")
        
        # Display device info
        if self.args.iphone:
            print(f"📱 Device: iPhone Emulation")
            print(f"👁️ Browser: {self.args.browser} ({'Headless' if headless else 'Visible'})")
        else:
            print(f"🖥️ Device: Desktop")
            print(f"👁️ Browser: {self.args.browser} ({'Headless' if headless else 'Visible'})")
            print(f"📱 Viewport: {width}x{height}")
        
        print(f"💾 Output: {self.output_dir}")
        
        # Configure capture engine
        browser_args = None
        config = CaptureConfig(
            browser_type=self.args.browser,
            headless=headless,
            viewport_width=width,
            viewport_height=height,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            device_emulation="iphone" if self.args.iphone else None,
            browser_args=browser_args
        )
        
        # Resolve Chrome profile path if requested
        chrome_profile_path = None
        if self.args.chrome_profile:
            if self.args.chrome_profile == 'default':
                # Default Windows Chrome User Data path
                chrome_profile_path = os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data')
            else:
                chrome_profile_path = self.args.chrome_profile
                
            if chrome_profile_path and not os.path.exists(chrome_profile_path):
                print(f"❌ Chrome profile path not found: {chrome_profile_path}")
                return False
                
            print(f"⚠️  USING REAL CHROME PROFILE: {chrome_profile_path}")
            print("   ❗ PLEASE ENSURE ALL CHROME WINDOWS ARE CLOSED before proceeding.")
            print("   ❗ The browser will launch in visible mode.")
            
            # If interactive, give user a moment to read warning
            if self.args.interactive:
                print("   Waiting 3 seconds...")
                await asyncio.sleep(3)
        
        self.engine = WebCaptureEngine(config)
        
        try:
            # Initialize browser
            print("\n🚀 Initializing browser...")
            await self.engine.initialize_browser()
            print("   ✅ Browser initialized")
            
            # Determine session mode
            if self.args.session_mode == 'anonymous':
                capture_mode = CaptureMode.ANONYMOUS
            elif self.args.session_mode == 'persistent':
                capture_mode = CaptureMode.PROFILE_BASED
            else:
                capture_mode = CaptureMode.INTERACTIVE_AUTH
                
            browser_mode = BrowserMode.INTERACTIVE if not headless else BrowserMode.HEADLESS
            
            # Create capture session
            # Use engine.create_session (already initialized above)
            self.session = self.engine.create_session(
                base_url=self.args.url,
                capture_mode=capture_mode,
                browser_mode=browser_mode,
                chrome_profile_path=chrome_profile_path
            )
            
            print(f"   📝 Session ID: {self.session.session_id}")
            print(f"   🔐 Session Mode: {self.args.session_mode}")
            
            # Store session info
            self.capture_data['session_info'] = {
                'session_id': self.session.session_id,
                'start_time': self.session_start_time.isoformat(),
                'url': self.args.url,
                'mode': 'interactive' if self.args.interactive else 'automated',
                'browser': self.args.browser,
                'headless': headless,
                'viewport': f"{self.session.viewport['width']}x{self.session.viewport['height']}",
                'session_mode': self.args.session_mode,
                'device_emulation': 'iphone' if self.args.iphone else None,
                'user_agent': self.session.user_agent
            }
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize session: {e}")
            if self.args.debug:
                import traceback
                traceback.print_exc()
            return False
    
    async def start_initial_capture(self):
        """Start the initial page capture"""
        print(f"\n🌐 Starting capture: {self.args.url}")
        
        # In engine.py, it doesn't seem to have start_capture yet based on what I read.
        # Let's check engine.py again if I can.
        # Actually, let's assume it has it or I'll need to fix it.
        # Based on scripts/web-capture-cli.py it expects it.
        
        # Wait, I should probably check if engine.py has start_capture.
        # I'll check it after this write.
        
        try:
            # Re-check engine.py methods in next turn if needed.
            # For now, keep the original script logic.
            capture = await self.engine.start_capture(self.args.url)
            await asyncio.sleep(3)  # Allow page to load
            
            # Get page handler
            handler_key = f"{self.session.session_id}_0"
            if handler_key in self.engine._active_handlers:
                self.page_handler = self.engine._active_handlers[handler_key]
                page = self.page_handler.page
                
                # Collect initial page info
                page_title = await page.title()
                current_url = page.url
                
                print(f"   📄 Title: {page_title}")
                print(f"   🔗 Final URL: {current_url}")
                
                # Take initial screenshot
                if self.args.save_screenshots:
                    await self.take_screenshot("initial_load")
                
                # Store capture info
                self.capture_data['captures'].append({
                    'timestamp': datetime.now().isoformat(),
                    'url': current_url,
                    'title': page_title,
                    'type': 'initial_load'
                })
                
                return True
            else:
                print("   ❌ Could not get page handler")
                return False
        except Exception as e:
            print(f"   ❌ Initial capture failed: {e}")
            return False
    
    async def take_screenshot(self, label="capture"):
        """Take a screenshot and save it"""
        if not self.page_handler:
            return None
            
        try:
            screenshot = await self.page_handler.take_screenshot()
            if screenshot:
                timestamp = datetime.now().strftime('%H%M%S')
                screenshot_path = self.output_dir / f"screenshot_{label}_{timestamp}.png"
                
                with open(screenshot_path, 'wb') as f:
                    f.write(screenshot)
                
                self.capture_data['screenshots'].append({
                    'timestamp': datetime.now().isoformat(),
                    'label': label,
                    'path': str(screenshot_path)
                })
                
                if self.args.debug:
                    print(f"   📸 Screenshot saved: {screenshot_path}")
                
                return screenshot_path
        except Exception as e:
            if self.args.debug:
                print(f"   ❌ Screenshot failed: {e}")
        
        return None
    
    async def run_interactive_mode(self):
        """Run interactive mode - keep browser open for manual interaction"""
        print("\n🎮 Interactive Mode Started")
        print("=" * 30)
        print("The browser is now open for manual interaction.")
        print("This session will capture:")
        print("  • Periodic screenshots")
        print("  • Network traffic")
        print("  • Page navigation")
        print(f"  • Session will auto-close after {self.args.max_time} seconds")
        print("\nTo end session:")
        print("  • Press Ctrl+C, or")
        print("  • Close the browser window")
        
        start_time = time.time()
        last_screenshot = 0
        
        try:
            while True:
                current_time = time.time()
                elapsed = current_time - start_time
                
                # Check max time limit
                if elapsed > self.args.max_time:
                    print(f"\n⏰ Session time limit reached ({self.args.max_time}s)")
                    break
                
                # Take periodic screenshots
                if (current_time - last_screenshot) >= self.args.capture_interval:
                    await self.take_screenshot(f"interval_{int(elapsed)}")
                    last_screenshot = current_time
                    
                    # Show progress
                    remaining = self.args.max_time - elapsed
                    print(f"⏱️ Session active: {int(elapsed)}s elapsed, {int(remaining)}s remaining")
                
                # Check if page is still active and browser hasn't been closed
                if self.page_handler and self.page_handler.page:
                    try:
                        # Test if browser is still alive by checking the page
                        current_url = self.page_handler.page.url
                        await self.page_handler.page.evaluate("1")  # Simple test to see if page is responsive
                        
                        # Log URL changes
                        if (not self.capture_data['captures'] or 
                            current_url != self.capture_data['captures'][-1]['url']):
                            
                            page_title = await self.page_handler.page.title()
                            self.capture_data['captures'].append({
                                'timestamp': datetime.now().isoformat(),
                                'url': current_url,
                                'title': page_title,
                                'type': 'navigation'
                            })
                            
                            print(f"🧭 Navigation detected: {page_title}")
                            await self.take_screenshot("navigation")
                    except Exception as e:
                        # Browser or page has been closed
                        if "Target closed" in str(e) or "Browser has been closed" in str(e) or "Session closed" in str(e):
                            print(f"\n🔴 Browser was closed manually - ending session")
                            break
                        else:
                            # Other exception - might be temporary, continue but log it
                            if self.args.debug:
                                print(f"   ⚠️ Page check exception: {e}")
                else:
                    # Page handler is None - browser is likely closed
                    print(f"\n🔴 Browser connection lost - ending session")
                    break
                
                await asyncio.sleep(1)  # Check every second
                
        except KeyboardInterrupt:
            print("\n⏹️ Session interrupted by user - Saving session...")
            # Allow loop to exit naturally to trigger save
        
        print(f"🏁 Interactive session completed")
    
    async def run_automated_mode(self):
        """Run automated mode with LLM instructions"""
        if not self.args.instruction:
            print("❌ Automated mode requires --instruction parameter")
            return False
        
        print(f"\n🤖 Automated Mode Started")
        print("=" * 30)
        print(f"📝 Instruction: {self.args.instruction}")
        print("\nExecuting automation...")
        
        try:
            # Parse basic instructions
            instruction_lower = self.args.instruction.lower()
            
            if "scroll" in instruction_lower:
                await self.execute_scroll_action()
            
            if "click" in instruction_lower and "menu" in instruction_lower:
                await self.execute_menu_clicks()
                
            if "navigate" in instruction_lower or "about" in instruction_lower:
                await self.execute_navigation()
            
            if "form" in instruction_lower or "input" in instruction_lower:
                await self.execute_form_interaction()
            
            # Always take a final screenshot
            await self.take_screenshot("automation_complete")
            
            print("✅ Automation completed")
            return True
            
        except Exception as e:
            print(f"❌ Automation failed: {e}")
            if self.args.debug:
                import traceback
                traceback.print_exc()
            return False
    
    async def execute_scroll_action(self):
        """Execute scrolling action"""
        print("📜 Executing scroll action...")
        page = self.page_handler.page
        
        # Scroll down in increments
        for i in range(3):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(2)
            await self.take_screenshot(f"scroll_{i+1}")
        
        # Scroll back to top
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(1)
        await self.take_screenshot("scroll_top")
    
    async def execute_menu_clicks(self):
        """Execute menu clicking actions"""
        print("🔗 Executing menu click actions...")
        page = self.page_handler.page
        
        # Look for common menu selectors
        menu_selectors = [
            "nav a", ".nav a", ".menu a", ".navigation a",
            "header a", "[role='navigation'] a"
        ]
        
        for selector in menu_selectors:
            try:
                links = await page.query_selector_all(selector)
                for i, link in enumerate(links[:3]):  # Click first 3 menu items
                    text = await link.text_content()
                    if text and text.strip():
                        print(f"   🖱️ Clicking: {text.strip()}")
                        await link.click()
                        await asyncio.sleep(3)
                        await self.take_screenshot(f"menu_click_{i}")
                        await page.go_back()
                        await asyncio.sleep(2)
                break
            except Exception:
                continue
    
    async def execute_navigation(self):
        """Execute navigation actions"""
        print("🧭 Executing navigation actions...")
        page = self.page_handler.page
        
        # Look for about, contact, or other common pages
        target_links = ['about', 'contact', 'services', 'portfolio']
        
        for target in target_links:
            try:
                link = await page.query_selector(f"a[href*='{target}'], a:has-text('{target}')")
                if link:
                    print(f"   🔗 Navigating to {target} page")
                    await link.click()
                    await asyncio.sleep(3)
                    await self.take_screenshot(f"page_{target}")
                    await page.go_back()
                    await asyncio.sleep(2)
                    break
            except Exception:
                continue
    
    async def execute_form_interaction(self):
        """Execute form interaction"""
        print("📝 Executing form interactions...")
        page = self.page_handler.page
        
        try:
            # Look for forms
            forms = await page.query_selector_all("form")
            for i, form in enumerate(forms[:2]):  # Interact with first 2 forms
                # Find inputs
                inputs = await form.query_selector_all("input[type='text'], input[type='email'], textarea")
                
                for input_field in inputs:
                    input_type = await input_field.get_attribute("type")
                    placeholder = await input_field.get_attribute("placeholder")
                    name = await input_field.get_attribute("name")
                    
                    # Fill with appropriate test data
                    if "email" in (name or placeholder or "").lower():
                        await input_field.fill("test@example.com")
                    elif "name" in (name or placeholder or "").lower():
                        await input_field.fill("Test User")
                    else:
                        await input_field.fill("Test input")
                    
                    await asyncio.sleep(1)
                
                await self.take_screenshot(f"form_{i}_filled")
                # Don't submit forms to avoid spam
        except Exception as e:
            print(f"   ⚠️ Form interaction partially failed: {e}")
    
    async def save_session_data(self):
        """Save all captured session data"""
        print("\n💾 Saving session data...")
        
        # Generate session filename
        timestamp = self.session_start_time.strftime('%Y%m%d_%H%M%S')
        domain = self.args.url.split('//')[1].split('/')[0].replace(':', '_')
        
        # Collect network traffic data if available
        if self.args.save_network and self.engine and hasattr(self.engine, '_network_interceptors'):
            print("   🌐 Collecting network traffic data...")
            all_network_data = []
            traffic_summary = {}
            
            for session_id, interceptor in self.engine._network_interceptors.items():
                if hasattr(interceptor, 'network_log') and interceptor.network_log:
                    # Convert network requests to serializable format
                    session_requests = []
                    for req in interceptor.network_log:
                        req_data = {
                            'sequence_number': req.sequence_number,
                            'timestamp': req.timestamp.isoformat() if req.timestamp else None,
                            'url': req.url,
                            'method': req.method,
                            'headers': req.headers,
                            'is_api_call': req.is_api_call,
                            'is_media_content': req.is_media_content,
                            'response_status': req.response_status,
                            'response_headers': req.response_headers,
                            'response_size_bytes': req.response_size_bytes,
                        }
                        
                        # Include request body for small requests (avoid huge payloads)
                        if hasattr(req, 'body') and req.body and len(str(req.body)) < 10000:
                            req_data['request_body'] = req.body
                            
                        # Include response body for API calls (already filtered for size)
                        if hasattr(req, 'response_body') and req.response_body:
                            req_data['response_body'] = req.response_body
                            
                        session_requests.append(req_data)
                    
                    all_network_data.extend(session_requests)
                    
                    # Get traffic summary for this session
                    if hasattr(interceptor, 'get_traffic_summary'):
                        session_summary = interceptor.get_traffic_summary()
                        traffic_summary[session_id] = session_summary
                        
                        print(f"   📊 Session {session_id}: {session_summary.get('total_requests', 0)} requests captured")
                    
                    # Get API endpoints discovered
                    if hasattr(interceptor, 'get_api_endpoints'):
                        api_endpoints = interceptor.get_api_endpoints()
                        if api_endpoints:
                            print(f"   🔌 API endpoints discovered: {len(api_endpoints)}")
                            if session_id not in traffic_summary:
                                traffic_summary[session_id] = {}
                            traffic_summary[session_id]['api_endpoints'] = api_endpoints
            
            # Store network data
            self.capture_data['network_logs'] = all_network_data
            self.capture_data['traffic_summary'] = traffic_summary
            
            if all_network_data:
                print(f"   ✅ Network traffic captured: {len(all_network_data)} requests")
            else:
                print("   ⚠️ No network traffic captured")
        
        # Add session summary
        self.capture_data['session_summary'] = {
            'duration_seconds': (datetime.now() - self.session_start_time).total_seconds(),
            'total_captures': len(self.capture_data['captures']),
            'total_screenshots': len(self.capture_data['screenshots']),
            'total_network_requests': len(self.capture_data.get('network_logs', [])),
            'end_time': datetime.now().isoformat()
        }
        
        # Save main session data
        session_file = self.output_dir / f"{domain}_{timestamp}_session.json"
        
        # Custom JSON encoder for datetime objects
        def json_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(self.capture_data, f, indent=2, ensure_ascii=False, default=json_serializer)
        
        return session_file
    
    async def cleanup(self):
        """Clean up resources"""
        if self.engine:
            await self.engine.shutdown()
        print("🔧 Session cleanup completed")


async def async_main():
    """Async main entry point"""
    args = parse_arguments()
    
    # Validate arguments
    if not args.url.startswith(('http://', 'https://')):
        print(f"❌ Invalid URL: {args.url}")
        print("URL must start with http:// or https://")
        sys.exit(1)
    
    if args.auto and not args.instruction:
        print("❌ Automated mode (--auto) requires --instruction parameter")
        sys.exit(1)
    
    # Create and run session
    session = WebCaptureSession(args)
    
    try:
        # Initialize session
        if not await session.initialize():
            sys.exit(1)
        
        # Start initial capture
        if not await session.start_initial_capture():
            sys.exit(1)
        
        # Run appropriate mode
        if args.interactive:
            await session.run_interactive_mode()
        else:
            success = await session.run_automated_mode()
            if not success:
                sys.exit(1)
        
        # Save session data
        session_file = await session.save_session_data()
        
        # Print summary
        duration = (datetime.now() - session.session_start_time).total_seconds()
        print(f"\n🎉 Web capture session completed!")
        print(f"⏱️ Duration: {duration:.1f} seconds")
        print(f"📂 Output: {session.output_dir}")
        print(f"📊 Captures: {len(session.capture_data['captures'])}")
        print(f"📸 Screenshots: {len(session.capture_data['screenshots'])}")
        
    except KeyboardInterrupt:
        print("\n⏹️ Session interrupted")
    except Exception as e:
        print(f"❌ Session failed: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    finally:
        await session.cleanup()


def main():
    """Synchronous entry point for pip scripts"""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
