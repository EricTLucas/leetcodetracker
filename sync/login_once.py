from playwright.sync_api import sync_playwright
import os

PROFILE_DIR = os.path.join(os.getcwd(), "playwright_profile")

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        PROFILE_DIR,
        headless=False,

        # These flags make Cloudflare treat the browser as real Chrome
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--start-maximized",
        ],

        # Pretend to be a real Chrome browser
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/127.0.0.1 Safari/537.36"
        ),

        # Make Playwright expose real browser APIs
        viewport={"width": 1280, "height": 800},
        java_script_enabled=True,
        bypass_csp=True,
    )

    page = browser.new_page()

    # Cloudflare sometimes needs a small delay before navigation
    page.wait_for_timeout(500)

    print("Opening LeetCode login page...")
    page.goto("https://leetcode.com/accounts/login/", wait_until="domcontentloaded")
    page.evaluate("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    """)

    print("Browser launched. Please log in manually.")
    print("After logging in, close the browser window.")
    input("Press Enter AFTER closing the browser...")

