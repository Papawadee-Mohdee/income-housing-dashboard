"""Script to capture visual verification screenshots using Playwright."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import threading
import time
import uvicorn
from playwright.sync_api import sync_playwright
from app.main import app

SCREENSHOTS_DIR = ROOT / "docs" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


class ServerThread(threading.Thread):
    def __init__(self, port=8877):
        super().__init__(daemon=True)
        self.port = port
        config = uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="warning")
        self.server = uvicorn.Server(config)

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True


def capture():
    port = 8877
    server_thread = ServerThread(port=port)
    server_thread.start()
    time.sleep(2)  # Wait for server to start

    base_url = f"http://127.0.0.1:{port}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1,
        )
        page = context.new_page()

        # 1. Tab 1 Light Default
        print("Capturing 01_tab1_light_default.png...")
        page.goto(f"{base_url}/?tab=1&theme=light&year=2568", wait_until="networkidle")
        page.wait_for_selector("#plot-choropleth .plot-container", timeout=15000)
        time.sleep(1.5)
        page.screenshot(path=str(SCREENSHOTS_DIR / "01_tab1_light_default.png"))

        # 2. Tab 1 Light Isan (region 4)
        print("Capturing 02_tab1_light_isan.png...")
        page.goto(f"{base_url}/?tab=1&theme=light&year=2568&region=4", wait_until="networkidle")
        page.wait_for_selector("#plot-choropleth .plot-container", timeout=15000)
        time.sleep(1.5)
        page.screenshot(path=str(SCREENSHOTS_DIR / "02_tab1_light_isan.png"))

        # 3. Tab 1 Dark Default
        print("Capturing 03_tab1_dark_default.png...")
        page.goto(f"{base_url}/?tab=1&theme=dark&year=2568", wait_until="networkidle")
        page.wait_for_selector("#plot-choropleth .plot-container", timeout=15000)
        time.sleep(1.5)
        page.screenshot(path=str(SCREENSHOTS_DIR / "03_tab1_dark_default.png"))

        # 4. Tab 2 Light Default
        print("Capturing 04_tab2_light_default.png...")
        page.goto(f"{base_url}/?tab=2&theme=light&year=2568", wait_until="networkidle")
        page.wait_for_selector("#plot-choropleth .plot-container", timeout=15000)
        time.sleep(1.5)
        page.screenshot(path=str(SCREENSHOTS_DIR / "04_tab2_light_default.png"))

        # 5. Tab 2 Dark Default
        print("Capturing 05_tab2_dark_default.png...")
        page.goto(f"{base_url}/?tab=2&theme=dark&year=2568", wait_until="networkidle")
        page.wait_for_selector("#plot-choropleth .plot-container", timeout=15000)
        time.sleep(1.5)
        page.screenshot(path=str(SCREENSHOTS_DIR / "05_tab2_dark_default.png"))

        # 6. Tab 3 Dark Default (Bonus verification)
        print("Capturing 06_tab3_dark_default.png...")
        page.goto(f"{base_url}/?tab=3&theme=dark&y0=2554&y1=2568", wait_until="networkidle")
        page.wait_for_selector("#plot-hero .plot-container", timeout=15000)
        time.sleep(1.5)
        page.screenshot(path=str(SCREENSHOTS_DIR / "06_tab3_dark_default.png"))

        browser.close()
        print("All screenshots successfully captured!")

    server_thread.stop()


if __name__ == "__main__":
    capture()
