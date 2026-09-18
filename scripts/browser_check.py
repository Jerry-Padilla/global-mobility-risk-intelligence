"""Run against a seeded local server; saves reviewable screenshots."""

import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

base = os.getenv("BASE_URL", "http://127.0.0.1:8000")
output = Path("docs/screenshots")
output.mkdir(parents=True, exist_ok=True)
deadline = time.monotonic() + 30
while True:
    try:
        with urllib.request.urlopen(base + "/health/", timeout=2) as response:
            if response.status == 200:
                break
    except (urllib.error.URLError, TimeoutError):
        if time.monotonic() >= deadline:
            raise RuntimeError(f"Application did not become healthy at {base}") from None
        time.sleep(0.5)
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    for route in (
        "/",
        "/suppliers/",
        "/factories/",
        "/global-risk/",
        "/supply-chain/",
        "/vehicle-safety/",
        "/recalls/",
        "/complaints/",
        "/analytics/",
        "/data-health/",
    ):
        response = page.goto(base + route, wait_until="networkidle")
        assert response.status == 200, (route, response.status)
        assert page.locator("h1").count() == 1
    page.goto(base, wait_until="networkidle")
    page.locator(".leaflet-interactive").first.wait_for()
    page.screenshot(path=str(output / "dashboard.png"), full_page=True)
    page.get_by_role("link", name="Explore the earthquake scenario").click()
    page.wait_for_load_state("networkidle")
    assert page.get_by_role("heading", name="4 / Compare sourcing options").count() == 1
    assert "Complete qualification before use" in page.locator("#options").inner_text()
    page.screenshot(path=str(output / "investigation.png"), full_page=True)
    investigation_url = page.url
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(investigation_url, wait_until="networkidle")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.set_viewport_size({"width": 1440, "height": 1100})
    page.goto(base, wait_until="networkidle")
    page.locator("a.entity-name").first.click()
    page.wait_for_load_state("networkidle")
    assert page.locator("h2", has_text="Component dependencies").count() == 1
    page.screenshot(path=str(output / "supplier.png"), full_page=True)
    page.locator('a[href^="/factories/"]').filter(has_text="Manufacturing").first.click()
    page.wait_for_load_state("networkidle")
    assert page.locator("text=Current utilization").count() == 1
    page.goto(base + "/suppliers/", wait_until="networkidle")
    page.locator('input[name="q"]').fill("Taiwan Precision")
    page.locator("button", has_text="Search").click()
    page.wait_for_function("document.querySelectorAll('#entity-results tbody tr').length === 1")
    assert "Taiwan Precision" in page.locator("#entity-results").inner_text()
    page.goto(base + "/vehicle-safety/", wait_until="networkidle")
    page.screenshot(path=str(output / "vehicle-safety.png"), full_page=True)
    page.locator('input[name="component"]').fill("BATTERY")
    page.locator("button", has_text="Apply filters").click()
    page.wait_for_load_state("networkidle")
    assert page.locator("text=No records match these filters.").count() == 1
    page.goto(base + "/global-risk/", wait_until="networkidle")
    page.locator(".leaflet-interactive").last.click(force=True)
    page.locator(".leaflet-popup-content a").click()
    page.wait_for_load_state("networkidle")
    assert "event=" in page.url
    assert page.locator("text=Investigating:").count() == 1
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(base, wait_until="networkidle")
    page.screenshot(path=str(output / "mobile.png"), full_page=True)
    overflow = page.evaluate(
        """Array.from(document.querySelectorAll('body *')).filter(e=>e.getBoundingClientRect().right>395).slice(0,15).map(e=>[e.tagName,String(e.className),e.getBoundingClientRect().width])"""
    )
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), overflow
    assert not errors, errors
    browser.close()
print("Browser checks passed: 10 routes, supplier investigation, map, charts, mobile layout")
