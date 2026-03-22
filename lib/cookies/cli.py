"""
Cookie Capture CLI
=================

Command-line interface for capturing browser cookies via CDP.
"""

import argparse
import asyncio
import sys
from typing import Optional

from .browser_launcher import BrowserLauncher, is_chrome_running, find_chrome, DEFAULT_CDP_PORT, DEFAULT_PROFILE_DIR
from .cdp_client import CDPClient, CDPError
from .profile_manager import ProfileManager


def parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Args:
        args: Optional argument list (uses sys.argv if None).
        
    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        prog="capture-cookies",
        description="Capture browser cookies via Chrome DevTools Protocol and save to profile file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s grok.com config/grok_profiles.json --cookies cf_clearance,sso,x-userid --key user_id
  %(prog)s peeks.com config/peeks_profiles.json --cookies session --key user_id --launch
  %(prog)s instagram.com config/instagram_profiles.json --cookies sessionid,csrftoken --key ds_user_id --auto

The tool connects to Chrome via CDP, extracts cookies for the specified domain,
and saves them to a JSON profile file. Profiles are matched by the --key field
to enable automatic updates when the same user logs in again.
        """,
    )
    
    # Positional arguments
    parser.add_argument(
        "domain",
        help="Domain to filter cookies (e.g., grok.com, peeks.com, instagram.com)",
    )
    parser.add_argument(
        "output_file",
        help="Path to JSON profiles file (e.g., config/grok_profiles.json)",
    )
    
    # Required options
    parser.add_argument(
        "--cookies",
        required=True,
        help="Comma-separated list of cookie names to capture (e.g., cf_clearance,sso,x-userid)",
    )
    parser.add_argument(
        "--key",
        required=True,
        dest="key_field",
        help="Cookie/field name used to identify unique profiles (e.g., user_id)",
    )
    
    # Optional flags
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_CDP_PORT,
        help=f"CDP remote debugging port (default: {DEFAULT_CDP_PORT})",
    )
    parser.add_argument(
        "--profile-dir",
        default=DEFAULT_PROFILE_DIR,
        help=f"Chrome user data directory (default: {DEFAULT_PROFILE_DIR})",
    )
    parser.add_argument(
        "--chrome",
        dest="chrome_path",
        help="Path to Chrome executable (default: auto-detect)",
    )
    parser.add_argument(
        "--launch",
        action="store_true",
        help="Launch Chrome if not running on CDP port",
    )
    parser.add_argument(
        "--close",
        action="store_true",
        help="Close browser after capturing cookies",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto-assign profile names (profile1, profile2...) for new users",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Poll interval in seconds (default: 5)",
    )
    parser.add_argument(
        "--mapping",
        help="Optional cookie-to-field name mapping (e.g., x-userid:user_id,session:session_id)",
    )
    
    return parser.parse_args(args)


def parse_cookie_mapping(mapping_str: Optional[str]) -> dict[str, str]:
    """
    Parse cookie-to-field mapping string.
    
    Args:
        mapping_str: Comma-separated "cookie:field" pairs.
        
    Returns:
        Dict mapping cookie names to field names.
    """
    if not mapping_str:
        return {}
    
    result = {}
    for pair in mapping_str.split(","):
        if ":" in pair:
            cookie, field = pair.split(":", 1)
            result[cookie.strip()] = field.strip()
    
    return result


async def async_main(args: argparse.Namespace) -> int:
    """
    Main async entry point.
    
    Args:
        args: Parsed command-line arguments.
        
    Returns:
        Exit code (0 for success, non-zero for error).
    """
    # Parse cookie names and mapping
    cookie_names = [c.strip() for c in args.cookies.split(",")]
    field_mapping = parse_cookie_mapping(args.mapping)
    
    # Build URL from domain
    url = f"https://{args.domain}/"
    
    print(f"Cookie Capture Tool")
    print(f"==================")
    print(f"  Domain: {args.domain}")
    print(f"  Cookies: {', '.join(cookie_names)}")
    print(f"  Key field: {args.key_field}")
    print(f"  Output: {args.output_file}")
    print()
    
    # Check or launch Chrome
    launcher = BrowserLauncher(
        chrome_path=args.chrome_path,
        profile_dir=args.profile_dir,
        port=args.port,
    )
    
    already_running = await is_chrome_running(args.port)
    
    if already_running:
        print(f"  Found Chrome on port {args.port} — connecting...")
    elif args.launch:
        chrome_path = launcher.chrome_path
        if not chrome_path:
            print(f"  ERROR: Chrome not found. Install Chrome or specify --chrome path.")
            return 1
        
        print(f"  Launching Chrome: {chrome_path}")
        print(f"  Profile: {args.profile_dir}")
        
        if not await launcher.launch_and_wait(url):
            print(f"  ERROR: Chrome did not start CDP within timeout.")
            return 1
        
        print(f"  Chrome launched. Opening {url}")
    else:
        print(f"  Chrome not detected on port {args.port}.")
        print(f"  Use --launch to start Chrome, or start it manually with:")
        print(f'    chrome --remote-debugging-port={args.port} --user-data-dir={args.profile_dir}')
        print()
        print(f"  Waiting for Chrome...")
        
        # Wait for manual browser launch
        for _ in range(60):  # Wait up to 30 seconds
            if await is_chrome_running(args.port):
                break
            await asyncio.sleep(0.5)
        else:
            print(f"  ERROR: Timeout waiting for Chrome on port {args.port}")
            return 1
    
    # Connect to CDP
    print(f"  Connecting to CDP...")
    
    try:
        cdp = CDPClient(port=args.port)
        await cdp.connect()
    except CDPError as e:
        print(f"  ERROR: {e}")
        return 1
    
    print(f"  Connected. Monitoring cookies (Ctrl+C to stop)...")
    print()
    
    # Setup profile manager
    manager = ProfileManager(args.output_file, args.key_field)
    
    last_cookies: dict[str, str] = {}
    waiting_printed = False
    
    try:
        while True:
            # Get cookies
            cookies = await cdp.get_cookies_with_mapping(
                args.domain,
                cookie_names,
                field_mapping,
            )
            
            # Check if we have the key field
            key_value = cookies.get(args.key_field)
            
            if not key_value:
                if not waiting_printed:
                    print(f"  Waiting for login... (navigate to {url} and sign in)")
                    waiting_printed = True
            elif cookies != last_cookies:
                # Cookies changed - save them
                waiting_printed = False
                
                # Resolve profile name
                profile_name = manager.find_profile_name_by_key(key_value)
                
                if profile_name:
                    key_display = key_value[:12] + "..." if len(key_value) > 15 else key_value
                    print(f"  Known user detected — profile '{profile_name}' ({args.key_field}: {key_display})")
                elif args.auto:
                    profile_name = manager.generate_profile_name()
                    key_display = key_value[:12] + "..." if len(key_value) > 15 else key_value
                    print(f"  New user detected — auto-assigning profile '{profile_name}' ({args.key_field}: {key_display})")
                else:
                    # Prompt for name
                    key_display = key_value[:12] + "..." if len(key_value) > 15 else key_value
                    profile_name = input(f"  New user detected ({args.key_field}: {key_display}). Enter profile name: ").strip()
                    if not profile_name:
                        profile_name = manager.generate_profile_name()
                        print(f"  Using auto-generated name: {profile_name}")
                
                # Display captured cookies
                if not last_cookies:
                    print(f"  Cookies captured:")
                else:
                    changed = [k for k in cookies if cookies.get(k) != last_cookies.get(k)]
                    print(f"  Cookie update detected ({', '.join(changed)}):")
                
                for field, value in sorted(cookies.items()):
                    display = value[:30] + "..." if len(value) > 33 else value
                    print(f"    {field}: {display}")
                
                # Save to profile
                manager.save_profile(profile_name, cookies)
                print(f"  Saved to {args.output_file}")
                print()
                
                last_cookies = cookies.copy()
                
                # Close browser if requested
                if args.close:
                    print(f"  --close specified. Exiting.")
                    break
            
            await asyncio.sleep(args.interval)
            
    except KeyboardInterrupt:
        print(f"\n  Interrupted by user.")
    except CDPError as e:
        print(f"\n  CDP error: {e}")
        return 1
    finally:
        await cdp.close()
        if args.close and args.launch:
            launcher.close()
    
    return 0


def main(args: Optional[list[str]] = None) -> int:
    """
    Main entry point.
    
    Args:
        args: Optional argument list (uses sys.argv if None).
        
    Returns:
        Exit code.
    """
    parsed = parse_args(args)
    
    try:
        return asyncio.run(async_main(parsed))
    except KeyboardInterrupt:
        return 130  # Standard Unix SIGINT exit code


if __name__ == "__main__":
    sys.exit(main())
