# KIA Token Generator

A script to automatically retrieve the Refresh Token from the Kia Connect system, which can be used instead of a password for authorization in applications.

## Requirements

- Python 3.7 or newer
- Google Chrome
- ChromeDriver (compatible with your Chrome version)

## Installation

1. **Install required libraries:**

```bash
pip install -r requirements.txt
```

2. **Install ChromeDriver:**

   - Download ChromeDriver from: https://chromedriver.chromium.org/downloads
   - Choose the version matching your Chrome version
   - Extract and add to PATH or place in the project directory

   **OR** use the automatic manager:
   ```bash
   pip install webdriver-manager
   ```
   
   Then modify the line in the code:
   ```python
   from webdriver_manager.chrome import ChromeDriverManager
   driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
   ```

## Usage

1. **Run the script:**

```bash
python KIA_TOKEN.py
```

2. **Log in manually:**
   - A Chrome browser window will open
   - Enter your Kia Connect login credentials
   - Wait for the script to automatically retrieve the token

3. **Copy the token:**
   - After successful login, the Refresh Token will be displayed
   - Copy it and use instead of your password in the application

## Example Output

```
Opening login page: https://idpconnect-eu.kia.com/auth/...

==================================================
Please log in manually in the browser window.
The script will wait for you to complete the login...
==================================================

✅ Login successful! Element found.

Navigating to redirect URL to get code...

Current URL after redirect: https://prd.eu-ccapi.kia.com:8080/api/...

✅ Authorization code extracted: abcd1234efgh5678ijkl...

==================================================
✅ SUCCESS!
==================================================

Use this token instead of your password:

eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

==================================================

Cleaning up and closing the browser.
```

## Troubleshooting

### Error: ChromeDriver not found
- Make sure ChromeDriver is installed and added to PATH
- Or use `webdriver-manager` as described in the installation section

### Error: Timeout during login
- The script waits up to 5 minutes for login completion
- Make sure you're logging in within the opened browser window

### Error: Could not find authorization code in URL
- Check if the login completed successfully
- Check your internet connection
- Try running the script again

### Error: Error getting tokens from der API
- The authorization token may be invalid or expired
- Try running the script again and log in from scratch

## Notes

- **Refresh Token is long** - this is normal! It can be 500-1000+ characters
- Store the token in a secure location
- Do not share the token with anyone
- The token may expire after some time - then run the script again

## Configuration Parameters

In the `KIA_TOKEN.py` file you can modify:

- `CLIENT_ID` - Kia API client ID
- `BASE_URL` - Authorization API base URL
- `LOGIN_URL` - Login page URL
- `REDIRECT_URL_FINAL` - Redirect URL after authorization

## License

Use at your own risk. The script is intended for personal use only.

