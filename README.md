# Kia Token Generator

Generate a refresh token for the **Kia Connect API (Europe)** to use with the [kia_uvo](https://github.com/Hyundai-Kia-Connect/kia_uvo) Home Assistant integration.

> **⚠️ This tool works ONLY for European Kia accounts.**  
> For Hyundai EU, see: [hyundai_kia_connect_api#925](https://github.com/Hyundai-Kia-Connect/hyundai_kia_connect_api/issues/925)

## What changed in v2.0

- **No more Selenium / ChromeDriver dependency** — uses Chrome's native DevTools Protocol (CDP) over WebSocket
- **Automatic locale detection** — login page language matches your system (override with `--locale pl`)
- **Dynamic state parameter** — no more hardcoded timestamps that could expire
- **Auto-install dependencies** — creates a local `.venv` and installs `requests` + `websocket-client` automatically
- **Retry with backoff** on token exchange errors (429, timeouts)
- **Works on Windows, macOS, and Linux** without extra setup beyond Chrome + Python

## Requirements

| Component | Version |
|-----------|---------|
| Python    | 3.8+    |
| Chrome    | Any recent version (Chromium also works) |

That's it. No ChromeDriver, no Selenium, no manual pip installs.

## Quick start

### Windows

```
python KIA_TOKEN.py
```

### macOS / Linux

```
python3 KIA_TOKEN.py
```

The script will:

1. Create a `.venv` and install dependencies automatically (first run only)
2. Open Chrome with the Kia login page
3. Wait for you to log in and complete the CAPTCHA
4. Ask you to confirm login is done
5. Automatically capture the authorization code
6. Exchange it for a refresh token
7. Display the token

### Command-line options

```
python KIA_TOKEN.py --locale de    # force German login page
python KIA_TOKEN.py --locale pl    # force Polish login page
python KIA_TOKEN.py --port 9333    # use different debugging port
python KIA_TOKEN.py --help
```

Supported locales: `de`, `en`, `fr`, `it`, `es`, `nl`, `pl`, `pt`, `cs`, `sk`, `hu`, `ro`, `bg`, `hr`, `sl`, `sv`, `no`, `da`, `fi`

## Using the token with Home Assistant

After getting your refresh token:

1. Go to **Settings → Devices & Services → + Add Integration**
2. Search for **Kia Uvo / Hyundai Bluelink**
3. Enter:
   - **Username**: your Kia Connect email address
   - **Password**: the **refresh token** from this script (NOT your Kia password)
   - **PIN**: leave **empty**
4. Submit — your car should appear

### Important notes for Home Assistant

- The refresh token is long (500–1000+ characters) — this is normal
- If the integration shows "unexpected error", generate a **fresh** token and try again
- After a Home Assistant **update**, the integration may need a new token
- The token expires after some time — run the script again when needed

## HAOS / Docker users

If you run Home Assistant OS (HAOS) or Home Assistant in Docker, you **do not** run this script inside HA. Run it on your **desktop/laptop** (Windows, macOS, or Linux with a browser), then copy the token into HA's integration setup.

### Step by step for HAOS users

1. On your **PC/Mac** (not on HA), download `KIA_TOKEN.py`
2. Run `python3 KIA_TOKEN.py` (or `python KIA_TOKEN.py` on Windows)
3. Log in to Kia in the Chrome window that opens
4. Copy the refresh token from the terminal output
5. In HA: **Settings → Devices & Services → Add Integration → Kia Uvo**
6. Paste the refresh token as the password

You do **not** need to modify any files inside HA containers or replace `KiaUvoApiEU.py` if you are using the latest version of the kia_uvo integration from HACS.

## Security

```
┌─────────────────────────────────────────────────────────────┐
│  NEVER publish your refresh token or access token!          │
│  Anyone with your token has FULL ACCESS to your Kia         │
│  account and can control your car (lock/unlock, location,   │
│  climate, etc.)                                             │
│                                                             │
│  If you accidentally leak your token:                       │
│  1. Change your Kia Connect password immediately            │
│  2. Generate a new token                                    │
│  3. Update Home Assistant with the new token                │
└─────────────────────────────────────────────────────────────┘
```

## Troubleshooting / FAQ

### "Chrome not found"

The script auto-detects Chrome in standard locations. If you installed Chrome in a non-standard path, add it to your system PATH or create a symlink.

### Error: `code=` not found / "Authorization code not found"

**Most common cause:** the user-agent was not applied correctly, or the login was not fully completed.

The script sets the user-agent automatically via Chrome launch flags. If it still fails:

- Make sure you **fully complete** the login (CAPTCHA + credentials) and wait until the Kia website loads
- Try a different network (VPN/firewall may block `prd.eu-ccapi.kia.com:8080`)
- Close **all** other Chrome windows before running the script (they may interfere with CDP)

### Error: "Existing Chrome debug session on port 9222"

Close all Chrome instances or use a different port:

```
python KIA_TOKEN.py --port 9333
```

### Error: "Token exchange failed" / HTTP 400

- The authorization code may have expired — run the script again
- Ensure you're using a **European** Kia account

### macOS: "Chrome cannot be opened because it is from an unidentified developer"

For Chromium installed via `brew`:

```
xattr -d com.apple.quarantine /Applications/Chromium.app
```

### Linux: "No graphical display detected"

This script needs a desktop environment. It cannot run on a headless server (e.g., inside a HA container or SSH without X forwarding). Run it on a machine with a monitor/display.

### Python version error on macOS

If you get `unsupported operand type(s) for |: 'type' and 'NoneType'`, your Python is older than 3.10. This script (v2.0) requires only 3.8+ and does not use `str | None` syntax, so this error should not occur. If it does, update Python:

```
brew install python
```

### Token expires — how often do I need to regenerate?

The token validity varies but is typically several hours to days. The HA integration should auto-refresh it. If the integration stops working, generate a new token.

### Does this work for Hyundai?

**No.** This script is for Kia EU only. For Hyundai EU, use one of these:

- [hyundai_kia_connect_api#925](https://github.com/Hyundai-Kia-Connect/hyundai_kia_connect_api/issues/925) — community solution with batch files
- [hyundai_kia_connect_api#959](https://github.com/Hyundai-Kia-Connect/hyundai_kia_connect_api/issues/959) — multiplatform CDP script (no Selenium)
- [Wiki: Hyundai Europe Login Flow](https://github.com/Hyundai-Kia-Connect/hyundai_kia_connect_api/wiki) (if available)

### I had `KiaFetchApiTokens.py` before — what's different?

The original `KiaFetchApiTokens.py` (by marvinwankersteen) requires manual steps: changing user-agent in Chrome DevTools, copying URLs between terminal and browser. This script automates those steps.

The Selenium-based `KiaFetchApiTokensSelenium.py` requires matching ChromeDriver versions, which caused most user issues. This script (v2.0) eliminates that entirely.

## How it works

1. Launches Chrome with `--remote-debugging-port` and a mobile user-agent (required by Kia's API)
2. Opens the Kia login page — you log in manually (CAPTCHA cannot be automated)
3. After login, navigates to the OAuth authorize endpoint via CDP WebSocket
4. Captures the redirect URL containing the authorization `code`
5. Exchanges the code for `access_token` + `refresh_token` via HTTP POST

## License

MIT — use at your own risk. This tool is for personal use only.

## Related

- [kia_uvo](https://github.com/Hyundai-Kia-Connect/kia_uvo) — Home Assistant integration
- [hyundai_kia_connect_api](https://github.com/Hyundai-Kia-Connect/hyundai_kia_connect_api) — Python API library
- [Wiki: Kia Europe Login Flow](https://github.com/Hyundai-Kia-Connect/hyundai_kia_connect_api/wiki/Kia-Europe-Login-Flow) — official workaround documentation
