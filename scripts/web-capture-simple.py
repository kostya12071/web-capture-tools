#!/usr/bin/env python3
"""
Web Capture CLI - Simplified Version
====================================

Simple browser automation for web capture tasks.
"""

import asyncio
import argparse
import sys
import re
from pathlib import Path

# Add parent directory to path for lib imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.capture.browser.manager import BrowserManager
from lib.capture.storage.models import CaptureConfig, CaptureSession, CaptureMode, BrowserMode, SessionStatus


async def run_reddit_scrolling(url: str, instruction: str):
    """Scroll Reddit page until 14+ day old posts are visible"""
    print(f"🤖 Starting Reddit scrolling automation")
    print(f"🌐 URL: {url}")
    print(f"📝 Task: {instruction}")
    
    # Create config for browser automation
    config = CaptureConfig(
        headless=False,  # Show browser for debugging
        timeout_seconds=60,
        wait_after_load_seconds=3,
        capture_screenshots=False,  # Don't need screenshots for this task
        capture_browser_storage=False
    )
    
    # Create session for browser context
    session = CaptureSession(
        base_url=url,
        capture_mode=CaptureMode.ANONYMOUS,
        browser_mode=BrowserMode.INTERACTIVE,
        name="Reddit Scrolling Session"
    )
    
    browser_manager = BrowserManager(config)
    
    try:
        # Initialize browser
        await browser_manager.initialize()
        
        # Create context and page
        context = await browser_manager.create_context(session)
        page = await browser_manager.create_page(session.session_id)
        
        # Navigate to URL
        print(f"🌐 Navigating to {url}")
        await page.goto(url, wait_until='networkidle')
        await asyncio.sleep(3)
        
        print("📜 Starting scrolling to find older posts...")
        
        max_scrolls = 30
        for i in range(max_scrolls):
            # Scroll down
            await page.evaluate("window.scrollBy(0, 1000)")
            await asyncio.sleep(2)
            
            # Get page content and check for post ages
            content = await page.content()
            
            # Look for day indicators
            day_matches = re.findall(r'(\d+)\s*days?\s*ago', content, re.IGNORECASE)
            
            if day_matches:
                days = [int(d) for d in day_matches]
                max_days = max(days)
                min_days = min(days)
                
                print(f"🗓️  Scroll {i+1}: Found posts {min_days}-{max_days} days old")
                
                if max_days >= 14:
                    print(f"✅ SUCCESS: Found posts {max_days} days old (target: 14+)")
                    print(f"📊 Total scrolls performed: {i+1}")
                    
                    # Get final statistics
                    all_days = sorted(set(days), reverse=True)
                    print(f"📈 Post age range: {all_days[:10]}... days ago")
                    return True
            else:
                print(f"🔄 Scroll {i+1}: No day indicators found yet")
            
            # Short pause between scrolls
            await asyncio.sleep(1)
        
        print(f"⚠️  Reached maximum scrolls ({max_scrolls}) without finding 14+ day old posts")
        return False
    
    finally:
        # Clean up browser resources
        await browser_manager.close_all()
        print("🧹 Browser cleanup completed")


async def basic_capture(url: str):
    """Basic URL capture without scrolling"""
    print(f"🌐 Loading URL: {url}")
    
    async with BrowserManager() as browser:
        page = await browser.create_page()
        
        response = await page.goto(url)
        print(f"📊 Status: {response.status}")
        
        content = await page.content()
        print(f"📄 Content length: {len(content)} bytes")
        
        return True


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Web Capture CLI - Browser automation for Reddit and other sites"
    )
    
    parser.add_argument('url', help='URL to capture')
    parser.add_argument('--auto', action='store_true', 
                       help='Enable automated mode')
    parser.add_argument('--instruction', 
                       help='Instruction for automation (e.g., "Scroll until 14 day old posts")')
    parser.add_argument('--interactive', action='store_true',
                       help='Enable interactive mode')
    
    args = parser.parse_args()
    
    if args.auto and args.instruction:
        # Automated mode with instructions
        if "reddit.com" in args.url and "scroll" in args.instruction.lower():
            asyncio.run(run_reddit_scrolling(args.url, args.instruction))
        else:
            print("❌ Automated instructions only supported for Reddit scrolling currently")
    elif args.interactive:
        print("❌ Interactive mode not yet implemented in simplified version")
    else:
        # Basic capture
        asyncio.run(basic_capture(args.url))


if __name__ == '__main__':
    main()
