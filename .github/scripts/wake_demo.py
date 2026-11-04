"""Open the hosted CareScribe demo in a real browser and wake it if it's asleep.

Streamlit Community Cloud puts apps to sleep after a stretch with no visitors.
A plain HTTP request doesn't count as a visit, so this uses a headless browser,
clicks the wake button when it shows up, and fails if the app never loads.
"""

import sys

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

URL = "https://care-note-assist.streamlit.app/"
WAKE_BUTTON = "Yes, get this app back up!"
READY_TEXT = "PHI leakage"  # shown on the app's main page once it has loaded


def app_is_up(page) -> bool:
    for frame in page.frames:
        try:
            if frame.get_by_text(READY_TEXT, exact=False).first.is_visible():
                return True
        except Exception:
            continue
    return False


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(8_000)

        button = page.get_by_role("button", name=WAKE_BUTTON)
        try:
            if button.is_visible():
                print("App was asleep. Clicking the wake button.")
                button.click()
        except PlaywrightTimeout:
            pass

        for _ in range(36):  # up to about 3 minutes
            if app_is_up(page):
                print("CareScribe demo is awake.")
                browser.close()
                return 0
            page.wait_for_timeout(5_000)

        page.screenshot(path="wake-failure.png", full_page=True)
        browser.close()
        print("CareScribe demo did not come up within 3 minutes.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
