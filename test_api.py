#!/usr/bin/env python3
"""Test script for Goodtop switch API."""

import hashlib
import os
import sys
import requests

# Check for password
if not os.environ.get("GOODTOP_PASS"):
    print("ERROR: GOODTOP_PASS environment variable not set!")
    print("Set it with: set GOODTOP_PASS=yourpassword")
    sys.exit(1)

BASE = os.environ.get("GOODTOP_HOST", "http://192.168.200.11")
USER = os.environ.get("GOODTOP_USER", "admin")
PASS = os.environ.get("GOODTOP_PASS", "")

TIMEOUT = 10


def get_cookie():
    return hashlib.md5(f"{USER}{PASS}".encode()).hexdigest()


def get_session():
    cookie = get_cookie()
    s = requests.Session()
    # Set cookie using the simpler approach - just set it in the jar
    s.cookies.set("admin", cookie)
    print(f"Cookie value: {cookie}")
    print(f"Cookies in session: {dict(s.cookies)}")
    return s


def test_fetch_pages():
    """Fetch and dump raw HTML from key pages."""
    s = get_session()

    # Do login first
    cookie = get_cookie()
    login_data = {
        "username": USER,
        "password": PASS,
        "language": "EN",
        "Response": cookie,
    }
    print(f"\nLogging in to {BASE}/login.cgi...")
    print(f"Login data: {login_data}")
    r = s.post(f"{BASE}/login.cgi", data=login_data, timeout=TIMEOUT)
    print(f"Login status: {r.status_code}")
    print(f"Login response cookies: {dict(s.cookies)}")

    pages = [
        ("port.cgi", "Port Settings"),
        ("port.cgi?page=stats", "Port Stats"),
        ("pse_port.cgi", "PoE Port Settings"),
        ("pse_system.cgi", "PoE System"),
    ]

    for page, desc in pages:
        print(f"\n{'='*60}")
        print(f"{desc} ({page})")
        print("="*60)
        try:
            r = s.get(f"{BASE}/{page}", timeout=TIMEOUT)
            print(f"Status: {r.status_code}")
            # Save to file for inspection
            filename = f"debug_{page.replace('?', '_').replace('=', '_')}.html"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(r.text)
            print(f"Saved to: {filename}")
            # Print first 2000 chars
            print(f"Content preview:\n{r.text[:2000]}")
        except Exception as e:
            print(f"Error: {e}")


def test_poe_toggle(port_id: int, enable: bool):
    """Test PoE toggle."""
    s = get_session()

    # Try login first
    cookie = get_cookie()
    login_data = {
        "username": USER,
        "password": PASS,
        "language": "EN",
        "Response": cookie,
    }
    print(f"\nLogging in...")
    r = s.post(f"{BASE}/login.cgi", data=login_data, timeout=TIMEOUT)
    print(f"Login status: {r.status_code}")

    # Now try PoE toggle
    poe_data = {
        "portid": str(port_id),
        "state": "1" if enable else "0",
        "submit": "apply",  # lowercase as per PowerShell
        "cmd": "poe",
        "language": "EN",
    }
    print(f"\nSending PoE toggle: {poe_data}")
    r = s.post(f"{BASE}/pse_port.cgi", data=poe_data, timeout=TIMEOUT)
    print(f"Response status: {r.status_code}")
    print(f"Response body:\n{r.text[:1500]}")


def test_port_toggle(port_id: int, enable: bool):
    """Test port enable/disable toggle."""
    s = get_session()

    # Try login first
    cookie = get_cookie()
    login_data = {
        "username": USER,
        "password": PASS,
        "language": "EN",
        "Response": cookie,
    }
    print(f"\nLogging in...")
    r = s.post(f"{BASE}/login.cgi", data=login_data, timeout=TIMEOUT)
    print(f"Login status: {r.status_code}")

    # Now try port toggle - matching PowerShell format exactly
    port_data = {
        "portid": str(port_id),
        "state": "1" if enable else "0",
        "speed_duplex": "0",  # Auto
        "flow": "0",  # Disabled
        "submit": "+++Apply+++",
        "cmd": "port",
    }
    print(f"\nSending port toggle: {port_data}")
    r = s.post(f"{BASE}/port.cgi", data=port_data, timeout=TIMEOUT)
    print(f"Response status: {r.status_code}")
    print(f"Response body:\n{r.text[:1500]}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  test_api.py fetch           # Fetch and dump all pages")
        print("  test_api.py poe <port> <0|1>  # Test PoE toggle")
        print("  test_api.py port <port> <0|1> # Test port toggle")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "fetch":
        test_fetch_pages()
    elif cmd == "poe" and len(sys.argv) == 4:
        test_poe_toggle(int(sys.argv[2]), sys.argv[3] == "1")
    elif cmd == "port" and len(sys.argv) == 4:
        test_port_toggle(int(sys.argv[2]), sys.argv[3] == "1")
    else:
        print("Invalid command")
