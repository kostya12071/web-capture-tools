#!/usr/bin/env python3
"""
Cookie Capture CLI
==================

Generic tool for capturing browser cookies via Chrome DevTools Protocol.

Usage:
    python capture-cookies.py <domain> <output_file> --cookies <names> --key <field> [options]

Examples:
    # Grok cookies
    python capture-cookies.py grok.com config/grok_profiles.json \\
        --cookies cf_clearance,sso,x-userid --key user_id --mapping x-userid:user_id --launch

    # Instagram cookies
    python capture-cookies.py instagram.com config/instagram_profiles.json \\
        --cookies sessionid,csrftoken,ds_user_id --key ds_user_id --launch --auto

    # Peeks cookies with existing browser
    python capture-cookies.py peeks.com config/peeks_profiles.json \\
        --cookies session --key user_id
"""

import sys
from pathlib import Path

# Add lib directory to path for direct script execution
script_dir = Path(__file__).parent
lib_dir = script_dir.parent / "lib"
if lib_dir.exists():
    sys.path.insert(0, str(lib_dir))

from cookies.cli import main

if __name__ == "__main__":
    sys.exit(main())
