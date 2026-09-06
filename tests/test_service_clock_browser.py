import json
from pathlib import Path
from unittest.mock import patch
from playwright.sync_api import sync_playwright, expect
from test_access import system


def test_repair_dialog_personal_photos_and_panel_layout(system):
    m, client = system
    m.save_settings(
        m.get_settings()["version"], {"services": ["chrony.service", "missing.service"]}
    )
    with m.connect() as db:
        for stamp, raw in db.execute(
            "SELECT timestamp,payload FROM samples"
        ).fetchall():
            data = json.loads(raw)
            data["services"].append(
                dict(
                    name="missing.service",
                    startup="not-found",
                    state="inactive",
                    running=False,
                )
            )
            db.execute(
                "UPDATE samples SET payload=? WHERE timestamp=?",
                (json.dumps(data), stamp),
            )
    photo = dict(
        city="London",
        artist="Test photographer",
        credit="Browser fixture",
        license="CC BY-SA 4.0",
        image_url="https://upload.wikimedia.org/test-city.svg",
        source_url="https://commons.wikimedia.org/wiki/File:Test.svg",
    )
    with patch.object(m, 'collect', side_effect=lambda: {**m.latest(), 'services': [{'name': 'chrony.service', 'running': True}]}), sync_playwright() as p, patch(
        "access_api.city_image", return_value=photo
    ), patch(
        "service_repairs.inspect_service",
        return_value={"LoadState": "not-found", "ActiveState": "inactive"},
    ), patch(
        "service_repairs.subprocess.run"
    ) as command:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        def route(route):
            r = route.request
            client.cookies.clear()
            response = client.request(
                r.method,
                r.url,
                headers=r.headers,
                content=r.post_data_buffer,
                follow_redirects=True,
            )
            route.fulfill(
                status=response.status_code,
                headers=dict(response.headers),
                body=response.content,
            )

        page.route("**/*", route)
        page.route("https://gravatar.com/**", lambda r: r.abort())
        page.route(
            "https://upload.wikimedia.org/**",
            lambda r: r.fulfill(
                content_type="image/svg+xml",
                body='<svg xmlns="http://www.w3.org/2000/svg" width="640" height="400"><rect width="640" height="400" fill="#289ac5"/><path d="M0 400V200H80V120H140V240H220V80H300V180H420V100H550V210H640V400" fill="#203349"/></svg>',
            ),
        )
        page.goto("https://testserver/")
        page.locator("[name=username]").fill("admin")
        page.locator("[name=password]").fill("admin")
        page.locator("#login-form button").click()
        expect(page.locator("#operating-system")).to_contain_text("Debian")
        os_box = page.locator(".system-information").nth(0).bounding_box()
        hw_box = page.locator(".system-information").nth(1).bounding_box()
        assert os_box["y"] == hw_box["y"] and hw_box["x"] > os_box["x"]
        page.locator("#world-panel > summary").click()
        expect(page.locator(".clock-city-background")).to_have_count(6)
        expect(page.locator(".clock-photo-credit").first).to_be_visible()
        page.locator(".clock-photo-credit").first.click()
        expect(page.locator("#city-photo-content")).to_contain_text("Test photographer")
        expect(page.locator('#city-photo-dialog .window-close')).to_have_css('padding','0px')
        expect(page.locator('#city-photo-dialog .window-close')).to_have_css('justify-content','center')
        page.screenshot(path=str(Path(__file__).resolve().parents[1]/'work/city-citation-53.png'),animations='disabled')
        page.get_by_role("button", name="Close Photo Credit").click()
        page.locator("#service-details-button").click()
        expect(
            page.get_by_role("button", name="Fix missing.service", exact=True)
        ).to_be_visible()
        expect(
            page.get_by_role("button", name="Fix chrony.service", exact=True)
        ).to_have_count(0)
        page.get_by_role("button", name="Fix missing.service", exact=True).click()
        expect(page.locator("#service-repair-message")).to_contain_text(
            "does not install"
        )
        page.get_by_role("button", name="Remove Health Check", exact=True).click()
        expect(page.locator("#service-repair-message")).to_contain_text(
            "Health check removed"
        )
        assert m.get_settings()["settings"]["services"] == ["chrony.service"]
        command.assert_not_called()
        page.get_by_role("button", name="Close Service Repair").click()
        page.get_by_role("button", name="Close Service Details").click()
        root = Path(__file__).resolve().parents[1]
        for theme in ("light", "dark"):
            page.evaluate(
                "(theme)=>document.documentElement.dataset.theme=theme", theme
            )
            page.screenshot(
                path=str(root / f"work/city-clock-{theme}.png"), full_page=True
            )
        page.set_viewport_size({"width": 390, "height": 844})
        assert (
            page.locator(".system-information").nth(1).bounding_box()["y"]
            > page.locator(".system-information").nth(0).bounding_box()["y"]
        )
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        page.get_by_role("button", name="Settings", exact=True).click()
        expect(page.locator("#clock-backgrounds")).to_be_checked()
        page.locator("#clock-backgrounds").uncheck()
        expect(page.locator("#clock-background-feedback")).to_have_text(
            "City backgrounds disabled."
        )
        page.get_by_role("link", name="Dashboard", exact=True).click()
        expect(page.locator("#operating-system")).to_contain_text("Debian")
        expect(page.locator(".clock-city-background")).to_have_count(0)
        assert errors == []
        browser.close()
