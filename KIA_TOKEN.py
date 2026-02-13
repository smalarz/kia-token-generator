#!/usr/bin/env python3
"""
Kia OAuth2 Token Fetcher — Chrome DevTools Protocol (no Selenium required)

Generates a refresh_token for Kia Connect EU integration with Home Assistant.
Uses Chrome's native remote debugging instead of Selenium/ChromeDriver.

Requirements: Python 3.8+ and Google Chrome (or Chromium)

Usage:
    python KIA_TOKEN.py              # interactive (default locale from system)
    python KIA_TOKEN.py --locale pl  # force Polish locale
    python KIA_TOKEN.py --help

Repository: https://github.com/smalarz/kia-token-generator
"""

import subprocess
import sys
import os
import platform
import time
import shutil
import re
import json
import tempfile
import locale
import argparse
import signal
from pathlib import Path
from typing import Optional, Dict, Any

# ---------------------------------------------------------------------------
# Python version gate
# ---------------------------------------------------------------------------
if sys.version_info < (3, 8):
    print(f"ERROR: Python 3.8+ is required (you have {sys.version})")
    print("Download: https://www.python.org/downloads/")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCRIPT_VERSION = "2.0.0"

CLIENT_ID = "fdc85c00-0a2f-4c64-bcb4-2cfb1500730a"
CLIENT_ID_LOGIN = "peukiaidm-online-sales"
BASE_URL = "https://idpconnect-eu.kia.com/auth/api/v2/user/oauth2/"
LOGIN_REDIRECT = "https://www.kia.com/api/bin/oneid/login"
REDIRECT_URL_FINAL = "https://prd.eu-ccapi.kia.com:8080/api/v1/user/oauth2/redirect"
TOKEN_URL = f"{BASE_URL}token"

USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 4.1.1; Galaxy Nexus Build/JRO03C) "
    "AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.166 "
    "Mobile Safari/535.19_CCS_APP_AOS"
)

SUPPORTED_LOCALES = [
    "de", "en", "fr", "it", "es", "nl", "pl", "pt", "cs", "sk",
    "hu", "ro", "bg", "hr", "sl", "sv", "no", "da", "fi",
]

CDP_PORT = 9222
CHROME_STARTUP_TIMEOUT = 20
LOGIN_TIMEOUT = 300  # 5 minutes
REDIRECT_TIMEOUT = 30
TOKEN_EXCHANGE_RETRIES = 3

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Kia OAuth2 Token Fetcher for Home Assistant integration"
    )
    parser.add_argument(
        "--locale",
        type=str,
        choices=SUPPORTED_LOCALES,
        default=None,
        help=f"UI language for Kia login page (default: auto-detect from system). "
             f"Supported: {', '.join(SUPPORTED_LOCALES)}",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=CDP_PORT,
        help=f"Chrome remote debugging port (default: {CDP_PORT})",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {SCRIPT_VERSION}",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Locale detection
# ---------------------------------------------------------------------------

def detect_locale() -> str:
    """Detect user locale from system settings, fallback to 'en'."""
    # Try environment variables first (works on all platforms)
    for var in ("LANG", "LANGUAGE", "LC_ALL", "LC_MESSAGES"):
        val = os.environ.get(var, "")
        if val:
            short = val[:2].lower()
            if short in SUPPORTED_LOCALES:
                return short

    # Try locale module (Python 3.11+ compatible)
    try:
        lang = locale.getlocale()[0]  # e.g. 'pl_PL', 'Polish_Poland'
        if lang:
            short = lang[:2].lower()
            if short in SUPPORTED_LOCALES:
                return short
    except Exception:
        pass

    return "en"


def build_login_url(ui_locale: str) -> str:
    """Build login URL with dynamic locale and fresh state parameter."""
    import base64
    state_raw = f"https://www.kia.com:443/?_tm={int(time.time() * 1000)}"
    state_b64 = base64.b64encode(state_raw.encode()).decode() + "_default"

    return (
        f"{BASE_URL}authorize?"
        f"ui_locales={ui_locale}&"
        f"scope=openid%20profile%20email%20phone&"
        f"response_type=code&"
        f"client_id={CLIENT_ID_LOGIN}&"
        f"redirect_uri={LOGIN_REDIRECT}&"
        f"state={state_b64}"
    )


def build_redirect_url() -> str:
    """Build OAuth redirect URL for code exchange."""
    return (
        f"{BASE_URL}authorize?"
        f"response_type=code&"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URL_FINAL}&"
        f"lang=en&state=ccsp"
    )


# ---------------------------------------------------------------------------
# Chrome path detection
# ---------------------------------------------------------------------------

def get_chrome_path() -> Optional[str]:
    """Find Chrome/Chromium executable for the current OS."""
    system = platform.system()
    candidates = {
        "Darwin": [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ],
        "Linux": [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
        ],
        "Windows": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            str(Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "Application" / "chrome.exe"),
            r"C:\Program Files\Chromium\Application\chrome.exe",
        ],
    }

    for path in candidates.get(system, []):
        if Path(path).exists():
            return path

    # Try PATH lookup as last resort
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        found = shutil.which(name)
        if found:
            return found

    return None


# ---------------------------------------------------------------------------
# Dependency management (auto-install into venv)
# ---------------------------------------------------------------------------

def ensure_dependencies() -> bool:
    """
    Ensure 'requests' and 'websocket-client' are importable.
    If not, create a local venv, install them, and re-exec this script inside it.
    """
    try:
        import requests  # noqa: F401
        import websocket  # noqa: F401
        return True
    except ImportError:
        pass

    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )

    if in_venv:
        # Inside venv but packages missing — install directly
        print("[INFO] Installing missing dependencies inside venv...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q", "requests", "websocket-client"]
        )
        return True

    # Not in venv — create one, install, re-exec
    venv_dir = Path(__file__).parent / ".venv"

    if not venv_dir.exists():
        print("[INFO] Creating virtual environment (.venv)...")
        try:
            subprocess.check_call([sys.executable, "-m", "venv", str(venv_dir)])
        except subprocess.CalledProcessError:
            print("[ERROR] Could not create venv. Install manually:")
            print("  pip install requests websocket-client")
            if platform.system() == "Linux":
                print("  (you may need: sudo apt install python3-venv)")
            sys.exit(1)

    venv_python = (
        venv_dir / "Scripts" / "python.exe"
        if sys.platform == "win32"
        else venv_dir / "bin" / "python"
    )

    # Install deps inside venv
    print("[INFO] Installing dependencies (requests, websocket-client)...")
    subprocess.check_call(
        [str(venv_python), "-m", "pip", "install", "-q", "requests", "websocket-client"]
    )

    # Re-execute this script under venv python
    print("[INFO] Restarting script inside virtual environment...\n")
    result = subprocess.run([str(venv_python)] + sys.argv, env=os.environ.copy())
    sys.exit(result.returncode)


# ---------------------------------------------------------------------------
# CDP helpers
# ---------------------------------------------------------------------------

def cdp_port_alive(port: int) -> bool:
    import requests
    try:
        r = requests.get(f"http://localhost:{port}/json", timeout=2)
        return r.status_code == 200
    except requests.exceptions.Timeout:
        return False
    except Exception:
        return False


def kill_existing_debug_session(port: int) -> None:
    if not cdp_port_alive(port):
        return
    print(f"[WARN] Existing Chrome debug session on port {port} — closing...")
    system = platform.system()
    try:
        if system == "Windows":
            subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"],
                           capture_output=True, timeout=5)
        else:
            subprocess.run(["pkill", "-f", f"--remote-debugging-port={port}"],
                           capture_output=True, timeout=5)
    except Exception:
        pass
    time.sleep(2)


def launch_chrome(login_url: str, port: int) -> subprocess.Popen:
    """Launch Chrome with remote debugging enabled."""
    chrome_path = get_chrome_path()
    if not chrome_path:
        print("[ERROR] Chrome/Chromium not found.")
        print("  Install: https://www.google.com/chrome/")
        sys.exit(1)

    # Check display on Linux
    if platform.system() == "Linux":
        if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            print("[ERROR] No graphical display detected (DISPLAY / WAYLAND_DISPLAY not set).")
            print("  This script requires a desktop environment with a browser.")
            sys.exit(1)

    kill_existing_debug_session(port)

    profile_dir = Path(tempfile.gettempdir()) / "kia-token-chrome-profile"
    if profile_dir.exists():
        shutil.rmtree(profile_dir, ignore_errors=True)
    profile_dir.mkdir(exist_ok=True)

    cmd = [
        str(chrome_path),
        f"--remote-debugging-port={port}",
        "--remote-allow-origins=*",
        f"--user-data-dir={profile_dir}",
        f"--user-agent={USER_AGENT}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-popup-blocking",
    ]

    # macOS: suppress Keychain prompts
    if platform.system() == "Darwin":
        cmd.append("--use-mock-keychain")

    cmd.append(login_url)

    print(f"[INFO] Launching Chrome (port {port})...")
    print(f"  Browser: {chrome_path}")

    kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if platform.system() == "Windows" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    process = subprocess.Popen(cmd, **kwargs)

    # Wait for CDP to become responsive
    for _ in range(CHROME_STARTUP_TIMEOUT):
        time.sleep(1)
        if cdp_port_alive(port):
            print("[INFO] Chrome ready.\n")
            return process

    print("[WARN] Chrome took longer than expected to start. Continuing anyway...")
    return process


def cdp_get_targets(port: int) -> list:
    import requests
    try:
        r = requests.get(f"http://localhost:{port}/json", timeout=5)
        return r.json()
    except Exception:
        return []


def cdp_navigate(port: int, url: str) -> bool:
    """Open a new tab navigating to the given URL via CDP."""
    import requests, websocket as ws_mod  # noqa: E401

    try:
        info = requests.get(f"http://localhost:{port}/json/version", timeout=5).json()
        browser_ws = info.get("webSocketDebuggerUrl")
        if not browser_ws:
            return False

        conn = ws_mod.create_connection(browser_ws, timeout=10)
        conn.send(json.dumps({
            "id": 1,
            "method": "Target.createTarget",
            "params": {"url": url},
        }))
        result = json.loads(conn.recv())
        conn.close()
        return "result" in result and "targetId" in result["result"]
    except Exception as e:
        print(f"[WARN] CDP navigation failed: {e}")
        return False


def cdp_find_code_url(port: int, preferred_prefix: Optional[str] = None, debug: bool = False) -> Optional[str]:
    """Search all CDP page targets for a URL containing 'code='.

    If preferred_prefix is provided, prefer URLs that start with it.
    """
    import requests, websocket as ws_mod  # noqa: E401

    try:
        info = requests.get(f"http://localhost:{port}/json/version", timeout=5).json()
        browser_ws = info.get("webSocketDebuggerUrl")
        if not browser_ws:
            return None

        conn = ws_mod.create_connection(browser_ws, timeout=10)
        conn.send(json.dumps({"id": 1, "method": "Target.getTargets", "params": {}}))
        result = json.loads(conn.recv())
        conn.close()

        targets = result.get("result", {}).get("targetInfos", [])
        pages = [t for t in targets if t.get("type") == "page"]

        preferred = None
        fallback = None

        for t in pages:
            url = t.get("url", "")
            if debug and "code=" in url:
                print(f"[DEBUG] Found code in URL: {url[:80]}...")
            if "code=" not in url:
                continue
            if preferred_prefix and url.startswith(preferred_prefix):
                if debug:
                    print(f"[DEBUG] Matched preferred prefix: {preferred_prefix[:50]}")
                preferred = url
                break
            if not fallback:
                fallback = url

        if preferred:
            return preferred
        if fallback:
            if debug:
                print(f"[DEBUG] Using fallback URL: {fallback[:80]}...")
            return fallback

        # fallback: return first page
        if pages:
            return pages[0].get("url")
    except Exception as e:
        if debug:
            print(f"[DEBUG] CDP error: {e}")
    return None


# ---------------------------------------------------------------------------
# Token exchange
# ---------------------------------------------------------------------------

def extract_auth_code(url: str) -> Optional[str]:
    """Extract the authorization code from a redirect URL."""
    # Specific UUID.UUID.UUID pattern first
    m = re.search(r"code=([0-9a-fA-F-]{36}\.[0-9a-fA-F-]{36}\.[0-9a-fA-F-]{36})", url)
    if m:
        return m.group(1)
    # Generic fallback
    m = re.search(r"code=([^&]+)", url)
    if m:
        return m.group(1)
    return None


def exchange_code_for_token(code: str) -> Optional[Dict[str, Any]]:
    """POST authorization code to token endpoint with retry and backoff."""
    import requests

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URL_FINAL,
        "client_id": CLIENT_ID,
        "client_secret": "secret",
    }

    for attempt in range(1, TOKEN_EXCHANGE_RETRIES + 1):
        try:
            resp = session.post(TOKEN_URL, data=data, timeout=30)

            if resp.status_code == 200:
                return resp.json()

            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 2 ** attempt))
                print(f"[WARN] Rate limited (429). Waiting {wait}s... (attempt {attempt}/{TOKEN_EXCHANGE_RETRIES})")
                time.sleep(wait)
                continue

            print(f"[WARN] Token exchange HTTP {resp.status_code} (attempt {attempt}/{TOKEN_EXCHANGE_RETRIES})")
            if attempt < TOKEN_EXCHANGE_RETRIES:
                time.sleep(2 ** attempt)
            else:
                print(f"[ERROR] Response body: {resp.text[:500]}")

        except requests.exceptions.Timeout:
            print(f"[WARN] Timeout (attempt {attempt}/{TOKEN_EXCHANGE_RETRIES})")
            if attempt < TOKEN_EXCHANGE_RETRIES:
                time.sleep(2 ** attempt)
        except Exception as e:
            print(f"[WARN] Error: {e} (attempt {attempt}/{TOKEN_EXCHANGE_RETRIES})")
            if attempt < TOKEN_EXCHANGE_RETRIES:
                time.sleep(2 ** attempt)

    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()

    ui_locale = args.locale or detect_locale()
    port = args.port

    print("=" * 60)
    print(f"  Kia Token Generator v{SCRIPT_VERSION}")
    print(f"  Region: EU | Locale: {ui_locale} | CDP port: {port}")
    print("=" * 60)
    print()

    # Build URLs
    login_url = build_login_url(ui_locale)
    redirect_url = build_redirect_url()

    # Launch Chrome
    chrome = launch_chrome(login_url, port)

    # Register cleanup on Ctrl+C
    def _cleanup(sig, frame):
        print("\n[INFO] Interrupted. Closing Chrome...")
        chrome.terminate()
        sys.exit(1)
    signal.signal(signal.SIGINT, _cleanup)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _cleanup)

    print("=" * 60)
    print("  A Chrome window has opened with the Kia login page.")
    print("  1. Log in with your Kia Connect credentials")
    print("  2. Complete the CAPTCHA")
    print("  3. Wait until the Kia website loads after login")
    print("=" * 60)
    print()

    try:
        answer = input("Have you completed the login? (Y/n): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        chrome.terminate()
        sys.exit(1)

    if answer and answer not in ("y", "yes", ""):
        print("[INFO] Cancelled.")
        chrome.terminate()
        sys.exit(0)

    # Navigate to OAuth redirect
    print("\n[INFO] Navigating to OAuth redirect URL...")
    if not cdp_navigate(port, redirect_url):
        print("[ERROR] Could not navigate Chrome to redirect URL.")
        chrome.terminate()
        sys.exit(1)

    # Wait for redirect with authorization code
    print("[INFO] Waiting for authorization code...")
    print(f"[DEBUG] Looking for redirect to: {REDIRECT_URL_FINAL}")
    code = None
    for i in range(REDIRECT_TIMEOUT):
        url = cdp_find_code_url(port, preferred_prefix=REDIRECT_URL_FINAL, debug=(i == 0 or i % 10 == 0))
        if url:
            code = extract_auth_code(url)
            if code:
                # Verify the URL matches the expected redirect
                if not url.startswith(REDIRECT_URL_FINAL):
                    print(f"[WARN] Got code from unexpected URL: {url[:80]}...")
                    print(f"[WARN] Expected URL to start with: {REDIRECT_URL_FINAL}")
                    print(f"[WARN] This may cause token exchange to fail. Continuing anyway...")
                break
        time.sleep(1)
        if i > 0 and i % 10 == 0:
            print(f"  Still waiting... ({i}s)")

    if not code:
        final_url = cdp_find_code_url(port, preferred_prefix=REDIRECT_URL_FINAL, debug=True) or "(unknown)"
        print(f"[ERROR] Authorization code not found in URL.")
        print(f"  Last URL: {final_url}")
        print()
        print("  Possible causes:")
        print("  - Login was not fully completed")
        print("  - Network/firewall blocking prd.eu-ccapi.kia.com:8080")
        print("  - Try a different network (e.g. mobile hotspot)")
        print("  - The OAuth redirect failed (check browser console for errors)")
        chrome.terminate()
        sys.exit(1)

    print(f"[OK] Authorization code: {code[:30]}...")

    # Exchange code for tokens
    print("\n[INFO] Exchanging code for tokens...")
    tokens = exchange_code_for_token(code)

    # Close Chrome
    chrome.terminate()
    try:
        chrome.wait(timeout=5)
    except subprocess.TimeoutExpired:
        chrome.kill()

    # Cleanup temp profile
    profile_dir = Path(tempfile.gettempdir()) / "kia-token-chrome-profile"
    if profile_dir.exists():
        shutil.rmtree(profile_dir, ignore_errors=True)

    if not tokens:
        print("[ERROR] Token exchange failed after all retries.")
        sys.exit(1)

    refresh_token = tokens.get("refresh_token")
    access_token = tokens.get("access_token")
    expires_in = tokens.get("expires_in")

    if tokens.get("error"):
        print(f"[ERROR] API error: {tokens['error']}")
        print(f"  Description: {tokens.get('error_description', 'N/A')}")
        sys.exit(1)

    if not refresh_token:
        print("[ERROR] No refresh_token in response.")
        print(f"  Response: {json.dumps(tokens, indent=2)}")
        sys.exit(1)

    # Success output
    print()
    print("=" * 60)
    print("  SUCCESS!")
    print("=" * 60)
    print()
    print("  Use this as your PASSWORD in Home Assistant")
    print("  when configuring the Kia UVO / Hyundai Bluelink integration:")
    print()
    print(f"  {refresh_token}")
    print()
    if expires_in:
        hours = expires_in // 3600
        print(f"  Expires in: {expires_in}s (~{hours}h)")
    print()
    print("  ┌─────────────────────────────────────────────────────┐")
    print("  │  SECURITY WARNING                                   │")
    print("  │  NEVER share this token publicly!                   │")
    print("  │  Anyone with this token has full access to your     │")
    print("  │  Kia account and your car.                          │")
    print("  └─────────────────────────────────────────────────────┘")
    print()
    print("  Home Assistant setup:")
    print("    Username: your Kia Connect email")
    print("    Password: the refresh token above")
    print("    PIN: leave empty")
    print()


if __name__ == "__main__":
    ensure_dependencies()
    main()
