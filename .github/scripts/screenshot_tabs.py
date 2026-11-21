"""Take screenshots of every tab of a locally running CareScribe app.

Used by the UI preview workflow so a pull request shows what the app looks
like before it is deployed. Expects the app at http://localhost:8501.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://localhost:8501/"
OUT = Path("screenshots")
TABS = ["Write a note", "Weekly summary", "Client history", "Health overview",
        "How it's tested", "About"]


def main() -> int:
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width, height, suffix in [(1440, 900, ""), (390, 844, "-mobile")]:
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(URL, wait_until="networkidle", timeout=60_000)
            page.get_by_text("rough shift notes", exact=False).first.wait_for(timeout=60_000)
            page.wait_for_timeout(2_500)  # let web fonts settle
            page.screenshot(path=OUT / f"00-front{suffix}.png")
            if suffix:
                page.screenshot(path=OUT / f"00-front{suffix}-full.png", full_page=True)
                page.close()
                continue
            page.set_viewport_size({"width": 1440, "height": 2200})
            for i, tab in enumerate(TABS, start=1):
                page.get_by_role("tab", name=tab).click()
                page.wait_for_timeout(1_500)
                name = tab.lower().replace("'", "").replace(" ", "-")
                page.screenshot(path=OUT / f"{i:02d}-{name}.png")
            page.close()
        browser.close()
    print(f"Saved {len(list(OUT.glob('*.png')))} screenshots.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
