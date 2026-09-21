"""Verify the standalone portfolio without Django, PostgreSQL or external requests."""

import functools
import http.server
import threading
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
(root / ".runtime").mkdir(exist_ok=True)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


server = http.server.ThreadingHTTPServer(
    ("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(root / "portfolio"))
)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_port}"
try:
    with TemporaryDirectory(dir=root / ".runtime") as recording, sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000},
            record_video_dir=recording,
            record_video_size={"width": 1280, "height": 890},
        )
        page = context.new_page()
        errors, failures, external = [], [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "response",
            lambda response: failures.append(response.url) if response.status >= 400 else None,
        )
        page.on(
            "request",
            lambda request: (
                external.append(request.url) if not request.url.startswith(base) else None
            ),
        )
        assert page.goto(base).status == 200
        page.screenshot(path=str(root / "docs/screenshots/portfolio.png"), full_page=True)
        page.wait_for_timeout(2000)
        page.get_by_role("link", name="Explore the sample").click()
        page.wait_for_timeout(2000)
        for title in [
            "One component connects two continents.",
            "Coverage is shorter than replenishment.",
            "A candidate is not yet a usable alternative.",
        ]:
            page.locator("#next-step").click()
            assert page.locator("#step-title").inner_text() == title
            page.wait_for_timeout(2500)
        initial = float(page.locator("#score").inner_text())
        assert initial >= 75
        page.locator("#alternative").check()
        assert abs(float(page.locator("#score").inner_text()) - (initial - 20)) < 0.11
        page.locator("#coverage").fill("30")
        page.locator("#coverage").dispatch_event("input")
        assert float(page.locator("#score").inner_text()) < 50
        page.wait_for_timeout(2500)
        page.get_by_role("button", name="Reset assumptions").click()
        assert float(page.locator("#score").inner_text()) == initial
        video = page.video
        await_url = page.url
        assert await_url.startswith(base)
        page.close()
        context.close()
        video.save_as(str(root / "portfolio/assets/walkthrough.webm"))
        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(base)
        assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth")
        mobile.get_by_role("button", name="04 The next move").click()
        assert mobile.locator("#fact-value").inner_text() == "Pending"
        mobile.screenshot(path=str(root / "docs/screenshots/portfolio-mobile.png"), full_page=True)
        no_js = browser.new_page(java_script_enabled=False)
        assert no_js.goto(base).status == 200
        assert no_js.locator("h1").is_visible()
        assert not errors, errors
        assert not failures, failures
        assert not external, external
        browser.close()
        print(
            "Portfolio passed: desktop/mobile, four-step journey, score behavior, offline assets, no-JS fallback"
        )
finally:
    server.shutdown()
