import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


def test_dashboard_controls():
    root = Path(__file__).resolve().parents[1]
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        state = {"healthy": True, "theme": "light"}
        shared = {"version":1,"settings":{"location":"London","latitude":51.5074,"longitude":-0.1278,"clocks":[{"name":"London","zone":"Europe/London"}]}}

        def route(request):
            path = request.request.url.split("localhost:8765")[-1].split("?")[0]
            now = int(time.time())
            tracking = {"Stratum": "2", "Reference ID": "GPS", "Last offset": "0.001 seconds", "RMS offset": "0.002 seconds", "Leap status": "Normal"}
            metrics = {"cpu": 12, "ram": 20, "storage": 4, "storage_used": 9000000000, "last_offset": 0.001, "rms_offset": 0.002, "ntp_rtt": 0.1, "temperature": 42, "uptime": 123456}
            if path == "/":
                request.fulfill(body=(root / "templates/index.html").read_text(encoding="utf-8").replace("{{ hostname }}", "CH84-SRV-NTP-01").replace("{{ dashboard_version }}", "3.0.0").replace("{{ api_version }}", "2.1.0"), content_type="text/html")
                return
            if path.endswith(".png"):
                request.fulfill(body=(root/path.lstrip("/")).read_bytes(),content_type="image/png")
                return
            if path.startswith("/static/"):
                request.fulfill(body=(root / path.lstrip("/")).read_text(encoding="utf-8"), content_type="image/svg+xml" if path.endswith("svg") else "text/css" if path.endswith("css") else "application/javascript")
                return
            if path == "/dashboard/settings":
                if request.request.method == "PATCH":
                    changes=request.request.post_data_json
                    shared["settings"].update({k:v for k,v in changes.items() if k!="version"})
                    shared["version"]+=1
                request.fulfill(json=shared)
                return
            payloads = {
                "/dashboard/status": {"healthy": state["healthy"], "metrics": metrics, "checks": {"required_services": state["healthy"]}, "services": [], "stale": False, "time_daemon": "Chrony", "gps": {"fix": "3D fix", "visible": 21, "used": 9, "pps": True}, "acquisition": {"selected": "PSM0"}},
                "/dashboard/tracking": {"status": "ok", "tracking": tracking},
                "/dashboard/clients": {"status": "ok", "timestamp": "2026-09-05T10:00:00Z", "clients": [{"addr": "10.0.0.1", "hostname": "test-client", "NTP": "12", "Drop": "0", "Last": "5"}]},
                "/dashboard/time": {"status": "ok", "timestamp": now, "round_trip_ms": 1},
                "/dashboard/solar": {"theme": state["theme"]},
                "/dashboard/history": {"samples": [{"timestamp": now - i * 30, "metrics": {**metrics, "cpu": 10 + i % 10}} for i in range(120, -1, -1)]},
            }
            request.fulfill(json=payloads.get(path, {}))

        page.route("**/*", route)
        page.goto("http://localhost:8765/")
        page.wait_for_function("document.getElementById('server-status').textContent === 'Server Online'")
        assert page.locator("h1").inner_text() == "TimeBeacon"
        assert not page.locator("#world-panel").evaluate("el => el.open")
        assert not page.locator("#clients-panel").evaluate("el => el.open")
        assert page.locator("#theme-toggle").count() == 0
        assert page.locator("#clock-zone option").count() > 400
        assert page.get_by_text("View 24-hour graph", exact=True).count() == 0
        assert page.locator("#system-storage").inner_text() == "9.0 GB (4.0%)"
        assert page.locator("#time-server-heading").inner_text() == "Chrony Time Server Status"
        assert page.locator("#acquisition-fix").inner_text() == "3D fix"
        assert page.locator("#acquisition-satellites").inner_text() == "9 used / 21 visible"
        page.locator("#service-details-button").click()
        assert page.locator("#service-details-dialog").is_visible()
        page.keyboard.press("Escape")
        page.locator(".toggle-control").click()
        assert page.locator("main details").evaluate_all("els=>els.every(el=>el.open)")
        assert page.locator(".client-card.open").count() == 1
        assert page.locator(".client-address").inner_text() == "test-client\n10.0.0.1"
        page.locator(".toggle-control").click()
        assert page.locator("main details").evaluate_all("els=>els.every(el=>!el.open)")
        assert page.locator(".client-card.open").count() == 0
        for key in ["last_offset", "rms_offset", "ntp_rtt"]:
            page.locator('[data-history="'+key+'"]').click()
            page.wait_for_selector("#history-graph path", state="attached")
            assert page.locator("#history-dialog").is_visible()
            assert page.locator("#history-graph text").last.text_content().endswith(("am", "pm"))
            page.keyboard.press("Escape")
        page.locator("#settings-button").click()
        page.locator("#setting-location").fill("Configured location")
        page.locator("#setting-latitude").fill("40.7")
        page.locator("#setting-longitude").fill("-74")
        state["theme"] = "dark"
        page.get_by_role("button", name="Save settings").click()
        page.wait_for_function("document.documentElement.dataset.theme === 'dark'")
        assert "Settings saved" in page.locator("#settings-feedback").inner_text()
        page.keyboard.press("Escape")
        page.locator("#world-panel > summary").click()
        page.locator("#clock-zone").select_option("Asia/Calcutta")
        page.get_by_role("button", name="Add clock", exact=True).click()
        expect(page.locator(".clock-offset").filter(has_text="UTC +05:30")).to_have_count(1)
        page.get_by_role("button", name="Remove Calcutta clock").click()
        expect(page.locator(".clock-offset").filter(has_text="UTC +05:30")).to_have_count(0)
        page.locator('[data-history="cpu"]').click()
        page.wait_for_selector("#history-graph path")
        assert "samples" in page.locator("#history-message").inner_text()
        assert page.locator("#history-duration option").all_text_contents() == ["Custom period", "15 Minutes", "30 Minutes", "60 Minutes", "2 Hours", "4 Hours", "8 Hours", "16 Hours", "24 Hours", "All of Time"]
        assert page.locator("#history-duration").input_value() == "60"
        assert page.locator("#history-latest, #history-all, #history-dialog input[type=range]").count() == 0
        for preset in ["15", "30", "60", "120", "240", "480", "960", "1440", "all"]:
            page.locator("#history-duration").select_option(preset)
            page.wait_for_selector("#history-graph path")
            assert page.locator("#history-duration").input_value() == preset
        page.locator("#history-duration").select_option("60")
        assert page.locator(".history-controls").bounding_box()["y"] > page.locator("#history-graph").bounding_box()["y"]
        assert page.locator(".clock-zone").first.inner_text() == "United Kingdom"
        assert page.evaluate("Intl.supportedValuesOf('timeZone').filter(zone=>!clockCountry(zone))") == []
        assert page.locator("#history-apply").count()==0
        page.locator("#history-start").fill("2026-09-01T10:00")
        page.locator("#history-start").blur()
        assert page.locator("#history-duration").input_value()=="custom"
        page.locator("#history-duration").select_option("60")
        page.screenshot(path=str(root / "work/graph-quick-ranges.png"), full_page=True)

        page.keyboard.press("Escape")
        state["healthy"] = False
        page.evaluate("refreshServer()")
        assert page.locator("#server-status").inner_text() == "Server Needs Attention"
        state["healthy"] = True
        page.evaluate("refreshServer()")
        page.locator("#world-panel > summary").click()
        page.screenshot(path=str(root / "work/preview-dark.png"), full_page=True)
        page.reload()
        page.wait_for_function("document.getElementById('server-status').textContent === 'Server Online'")
        assert page.evaluate("settings.location") == "Configured location"
        assert not page.locator("#world-panel").evaluate("el => el.open")
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(root / "work/preview-mobile.png"), full_page=True)
        assert errors == []
        browser.close()
