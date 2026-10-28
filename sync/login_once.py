"""Optional login helper; normal sync also prompts when sign-in expires."""
from playwright.sync_api import sync_playwright
from client import LeetCodeClient
from browser import launch_browser, close_browser
from sync import USERNAME

if __name__ == "__main__":
    with sync_playwright() as p:
        context = launch_browser(p)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://leetcode.com/", wait_until="domcontentloaded")
            LeetCodeClient(context).ensure_login(page, USERNAME)
            print("Login saved. You can now run sync.cmd.")
        finally:
            close_browser(context)
