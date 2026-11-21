"""Click through a locally running CareScribe app and screenshot every tab.

Used by the UI preview workflow so a pull request shows what the app looks
like before it is deployed, at desktop and phone widths. It also fails the
job if any step shows a Streamlit error. Expects the app at
http://localhost:8501.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://localhost:8501/"
OUT = Path("screenshots")
TABS = ["Write a note", "Weekly summary", "Client history", "Health overview",
        "How it's tested", "About"]
VIEWPORTS = [("desktop", 1440, 2200), ("phone", 390, 2400)]
errors = []


def check(page, step):
    if page.locator('[data-testid="stException"]').count():
        errors.append(step)
        print(f"Error shown after: {step}")


def pick(page, label, option):
    """Choose an option in a Streamlit selectbox by its label."""
    page.get_by_label(label, exact=True).first.click()
    page.get_by_role("option", name=option, exact=True).click()
    page.wait_for_timeout(1_200)


def main() -> int:
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, width, height in VIEWPORTS:
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.goto(URL, wait_until="networkidle", timeout=60_000)
            page.get_by_text("rough shift notes", exact=False).first.wait_for(timeout=60_000)
            page.wait_for_timeout(2_500)  # let web fonts settle
            page.screenshot(path=OUT / f"{name}-00-front.png")
            check(page, f"{name}: load")
            page.set_viewport_size({"width": width, "height": height})
            for i, tab in enumerate(TABS, start=1):
                page.get_by_role("tab", name=tab).click()
                page.wait_for_timeout(1_500)
                check(page, f"{name}: {tab}")
                slug = tab.lower().replace("'", "").replace(" ", "-")
                page.screenshot(path=OUT / f"{name}-{i:02d}-{slug}.png")
            if name == "desktop":
                page.get_by_role("tab", name="Write a note").click()
                pick(page, "Example", "A family call and a case worker's email")
                check(page, "example: family call")
                page.screenshot(path=OUT / "desktop-07-example-2.png")
                page.get_by_text("Your own notes", exact=True).click()
                page.wait_for_timeout(1_200)
                check(page, "own notes mode")
                page.screenshot(path=OUT / "desktop-08-own-notes.png")
            page.close()
        browser.close()
    print(f"Saved {len(list(OUT.glob('*.png')))} screenshots.")
    if errors:
        print("Steps that showed an error:", ", ".join(errors))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
