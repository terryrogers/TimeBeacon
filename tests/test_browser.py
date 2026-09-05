from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from test_access import system, login, change


def test_authenticated_dashboard_and_admin(system):
    m, client = system
    root = Path(__file__).resolve().parents[1]
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        def route(route):
            r = route.request
            client.cookies.clear()
            response = client.request(
                r.method, r.url, headers=r.headers, content=r.post_data_buffer
            )
            route.fulfill(
                status=response.status_code,
                headers=dict(response.headers),
                body=response.content,
            )

        page.route("**/*", route)
        page.goto("https://testserver/")
        expect(page.locator("#login-dialog")).to_be_visible()
        page.locator("#login-form [name=username]").fill("admin")
        page.locator("#login-form [name=password]").fill("admin")
        page.locator("#login-form button").click()
        page.wait_for_function(
            "document.getElementById('server-status').textContent==='Server Online'"
        )
        page.get_by_role("button", name="Administration", exact=True).click()
        expect(page.locator("#admin-dialog")).to_be_visible()
        page.locator("#admin-user-form [name=username]").fill("viewer")
        page.locator("#admin-user-form [name=password]").fill("viewer-password")
        page.locator("#admin-user-form button").first.click()
        expect(page.locator("#admin-feedback")).to_have_text("User saved.")
        page.keyboard.press("Escape")
        page.locator("[data-history=cpu]").click()
        page.wait_for_selector("#history-graph path", state="attached")
        expect(page.locator("#history-title")).to_have_text("Historic CPU Usage")
        expect(page.locator("#history-gap")).to_have_text("")
        assert page.locator("#history-count").inner_text().endswith(" samples")
        page.locator("#history-duration").select_option("1440")
        page.wait_for_function(
            "document.getElementById('history-gap').textContent==='Gaps indicate unavailable data.'"
        )
        page.locator("#history-start").fill("2026-09-01T10:00")
        page.locator("#history-start").blur()
        expect(page.locator("#history-duration")).to_have_value("custom")
        page.locator("#history-duration").select_option("60")
        page.wait_for_selector("#history-graph path", state="attached")
        page.screenshot(path=str(root / "work/rbac-graph.png"), full_page=True)
        page.get_by_role("button", name="Close graph").click()
        page.get_by_role("button", name="User Settings", exact=True).click()
        page.locator("#clock-zone").select_option("UTC")
        page.get_by_role("button", name="Add clock", exact=True).click()
        expect(page.locator("#clock-feedback")).to_have_text(
            "Clock added to your account."
        )
        page.locator("#key-form [name=name]").fill("browser test")
        page.locator("#key-form button").click()
        page.wait_for_function(
            "document.getElementById('new-key').textContent.includes('Copy now')"
        )
        page.get_by_role("button", name="Revoke", exact=True).click()
        expect(page.locator("#key-list button")).to_have_count(0)
        page.keyboard.press("Escape")
        page.get_by_role("button", name="Sign out", exact=True).click()
        expect(page.locator("#login-dialog")).to_be_visible()
        page.locator("#login-form [name=username]").fill("viewer")
        page.locator("#login-form [name=password]").fill("viewer-password")
        page.locator("#login-form button").click()
        page.wait_for_function(
            "document.getElementById('server-status').textContent==='Server Online'"
        )
        expect(
            page.get_by_role("button", name="Administration", exact=True)
        ).to_have_count(0)
        page.locator("#clients-panel > summary").click()
        expect(page.locator("#clients-count")).to_have_text("1")
        expect(page.locator("#client-grid")).not_to_be_visible()
        assert page.locator(".client-card").count() == 0
        page.get_by_role("button", name="User Settings", exact=True).click()
        expect(page.locator("#clock-form")).not_to_be_visible()
        expect(page.locator("#key-section")).not_to_be_visible()
        expect(page.locator("#clock-settings-list")).to_be_empty()
        page.keyboard.press("Escape")
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(root / "work/rbac-mobile.png"), full_page=True)
        assert errors == []
        browser.close()
