from playwright.sync_api import sync_playwright
import re
import os

PROFILE_DIR = os.path.join(os.getcwd(), "sync/playwright_profile")

def scrape_code_and_percentiles(submission_id):
    url = f"https://leetcode.com/submissions/detail/{submission_id}/"

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            PROFILE_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )

        page = browser.new_page()
        page.goto(url)

        # Wait for percentiles (hydrated DOM)
        page.wait_for_selector(
            'span[class*="text-lg"][class*="font-semibold"][class*="text-sd-foreground"]',
            timeout=60000
        )

        # Extract percentiles
        spans = page.evaluate("""
        () => Array.from(
            document.querySelectorAll('span[class*="text-lg"][class*="font-semibold"][class*="text-sd-foreground"]')
        ).map(el => el.innerText.trim());
        """)

        runtime_pct = spans[1] if len(spans) > 1 else None
        memory_pct = spans[3] if len(spans) > 3 else None

        # Extract code from Prism <code> block
        page.wait_for_selector("code[class^='language-']", timeout=60000)
        code_raw = page.locator("code[class^='language-']").inner_text()
        code = normalize_code(code_raw)
        browser.close()

        return {
            "id": submission_id,
            "code": code,
            "runtime_percentile": runtime_pct,
            "memory_percentile": memory_pct
        }

def normalize_code(raw):
    if raw is None:
        return None

    # Convert literal \n into actual newlines
    code = raw.replace("\\n", "\n")

    # Remove leading line numbers like "1", "2", "10", "57"
    code = re.sub(r"^\d+", "", code, flags=re.MULTILINE)

    # Strip accidental leading/trailing whitespace
    code = code.strip()

    return code




