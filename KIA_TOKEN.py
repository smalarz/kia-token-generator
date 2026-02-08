# main.py
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import requests

session = requests.Session()
CLIENT_ID = "fdc85c00-0a2f-4c64-bcb4-2cfb1500730a"
BASE_URL = "https://idpconnect-eu.kia.com/auth/api/v2/user/oauth2/"
LOGIN_URL = f"{BASE_URL}authorize?ui_locales=de&scope=openid%20profile%20email%20phone&response_type=code&client_id=peukiaidm-online-sales&redirect_uri=https://www.kia.com/api/bin/oneid/login&state=aHR0cHM6Ly93d3cua2lhLmNvbTo0NDMvZGUvP21zb2NraWQ9MjM1NDU0ODBmNmUyNjg5NDIwMmU0MDBjZjc2OTY5NWQmX3RtPTE3NTYzMTg3MjY1OTImX3RtPTE3NTYzMjQyMTcxMjY=_default"
SUCCESS_ELEMENT_SELECTOR = "a[class='logout user']"
REDIRECT_URL_FINAL = "https://prd.eu-ccapi.kia.com:8080/api/v1/user/oauth2/redirect"
REDIRECT_URL = f"{BASE_URL}authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URL_FINAL}&lang=de&state=ccsp"
TOKEN_URL = f"{BASE_URL}token"

def main():
    """
    Main function to run the Selenium automation.
    """
    # Initialize the Chrome WebDriver
    # Make sure you have chromedriver installed and in your PATH,
    # or specify the path to it.
    options = webdriver.ChromeOptions()
    options.add_argument("user-agent=Mozilla/5.0 (Linux; Android 4.1.1; Galaxy Nexus Build/JRO03C) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.166 Mobile Safari/535.19_CCS_APP_AOS")
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()

    # 1. Open the login page
    print(f"Opening login page: {LOGIN_URL}")
    driver.get(LOGIN_URL)

    print("\n" + "="*50)
    print("Please log in manually in the browser window.")
    print("The script will wait for you to complete the login...")
    print("="*50 + "\n")

    try:
        wait = WebDriverWait(driver, 300) # 300-second timeout
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, SUCCESS_ELEMENT_SELECTOR)))
        print("✅ Login successful! Element found.")

        # Navigate to redirect URL to get authorization code
        print(f"\nNavigating to redirect URL to get code...")
        driver.get(REDIRECT_URL)

        # Wait for URL to change and contain 'code' parameter
        try:
            wait = WebDriverWait(driver, 30) # 30-second timeout
            wait.until(lambda driver: 'code=' in driver.current_url or 'error' in driver.current_url)
        except TimeoutException:
            print("❌ Timed out waiting for authorization code redirect. Please ensure you complete the login process within 30 seconds.")
            return

        current_url = driver.current_url
        print(f"\nCurrent URL after redirect: {current_url}\n")

        # Check if there's an error in the URL
        if 'error' in current_url:
            error_match = re.search(r'error=([^&]+)', current_url)
            if error_match:
                print(f"❌ Error in authorization: {error_match.group(1)}")
            else:
                print(f"❌ Error in URL but couldn't parse it")
            return

        # Try to extract the authorization code
        # First try the specific format with dots
        code_match = re.search(
                r'code=([0-9a-fA-F-]{36}\.[0-9a-fA-F-]{36}\.[0-9a-fA-F-]{36})',
                current_url
            )

        # If not found, try a more generic pattern
        if not code_match:
            code_match = re.search(r'code=([^&]+)', current_url)

        if not code_match:
            print(f"❌ Could not find authorization code in URL!")
            print(f"URL was: {current_url}")
            return

        code = code_match.group(1)
        print(f"✅ Authorization code extracted: {code[:20]}...")
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URL_FINAL,
            "client_id": CLIENT_ID,
            "client_secret": "secret",
        }
        response = session.post(TOKEN_URL, data=data)
        if response.status_code == 200:
            tokens = response.json()
            if tokens is not None:
                refresh_token = tokens.get("refresh_token")
                if refresh_token:
                    print(f"\n{'='*50}")
                    print(f"✅ SUCCESS!")
                    print(f"{'='*50}")
                    print(f"\nUse this token instead of your password:\n")
                    print(f"{refresh_token}")
                    print(f"\n{'='*50}\n")
                else:
                    print(f"❌ Refresh token not found in response!")
                    print(f"Response: {tokens}")
        else:
            print(f"\n❌ Error getting tokens from the API!")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")

    except TimeoutException:
        print("❌ Timed out after 5 minutes. Login was not completed or the success element was not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        print("Cleaning up and closing the browser.")
        driver.quit()

if __name__ == "__main__":
    main()