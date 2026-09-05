import io
from unittest.mock import patch
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
            with patch(
                "account_api.urllib.request.urlopen",
                return_value=io.BytesIO(b'{"address":{"city":"Manchester"}}'),
            ):
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
        page.goto("https://testserver/")
        expect(page.locator("#login-form")).to_be_visible()
        expect(page.locator("#system-cpu")).to_have_count(0)
        page.screenshot(
            path=str(root / "work/semantic-login.png"),
            full_page=True,
            animations="disabled",
        )
        page.locator("#login-form [name=username]").fill("admin")
        page.locator("#login-form [name=password]").fill("admin")
        page.locator("#login-form button").click()
        page.wait_for_function(
            "document.getElementById('server-status')?.textContent==='Server Online'"
        )
        page.screenshot(
            path=str(root / "work/semantic-dashboard-light.png"),
            full_page=True,
            animations="disabled",
        )
        page.evaluate("document.documentElement.dataset.theme='dark'")
        expect(page.locator("[data-history=cpu]")).to_have_css(
            "background-color", "rgb(21, 34, 54)"
        )
        expect(page.locator("#settings-button")).to_have_css(
            "background-color", "rgb(30, 48, 71)"
        )
        page.screenshot(
            path=str(root / "work/semantic-dashboard-dark.png"),
            full_page=True,
            animations="disabled",
        )
        page.evaluate("document.documentElement.dataset.theme='light'")
        page.get_by_role("button", name="Administration", exact=True).click()
        page.get_by_role("link", name="Users", exact=True).click()
        page.get_by_role("button", name="New user", exact=True).click()
        expect(page.locator("#edit-user-dialog")).to_be_visible()
        page.locator("#admin-user-form [name=username]").fill("viewer")
        page.locator("#admin-user-form [name=password]").fill("viewer-password")
        page.locator("#admin-user-form button").first.click()
        expect(page.locator("#page-feedback")).to_have_text("User saved.")
        page.screenshot(
            path=str(root / "work/semantic-users.png"),
            full_page=True,
            animations="disabled",
        )
        page.get_by_role("link", name="Dashboard", exact=True).click()
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
        page.screenshot(
            path=str(root / "work/semantic-graph.png"),
            full_page=True,
            animations="disabled",
        )
        page.locator("#history-details").evaluate(
            "e=>{const p=document.createElement('p');p.style.height='1800px';e.append(p);}"
        )
        before = page.locator("#history-dialog .window-titlebar").bounding_box()
        page.locator("#history-dialog .window-content").evaluate(
            "e=>e.scrollTop=e.scrollHeight"
        )
        after = page.locator("#history-dialog .window-titlebar").bounding_box()
        assert before["y"] == after["y"]
        footer = page.locator("#history-dialog .window-statusbar").bounding_box()
        assert footer["y"] + footer["height"] <= 1000
        page.get_by_role("button", name="Close graph").click()
        page.get_by_role("button", name="User Settings", exact=True).click()
        page.wait_for_selector("#location-label")
        expect(page.locator("input[name=latitude]")).to_have_count(0)
        page.context.grant_permissions(["geolocation"])
        page.context.set_geolocation({"latitude": 53.4808, "longitude": -2.2426})
        page.get_by_role("button", name="Get my location", exact=True).click()
        expect(page.locator("#location-label")).to_have_text("Manchester")
        page.locator("#profile-form [name=name]").fill("Terry Rogers")
        page.get_by_role("button", name="Save profile", exact=True).click()
        expect(page.locator("#page-feedback")).to_have_text("Profile saved.")
        page.locator("#two-factor-form [name=password]").fill("admin")
        page.get_by_role("button", name="Register authenticator", exact=True).click()
        expect(page.locator("#two-factor-dialog")).to_be_visible()
        expect(page.locator("#enrollment-qr")).to_be_visible()
        page.get_by_role("button", name="Close registration").click()
        expect(page.locator("#enrollment-secret")).to_be_empty()
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
        page.get_by_role("button", name="Sign out", exact=True).click()
        expect(page.locator("#login-form")).to_be_visible()
        expect(page.locator("#system-cpu")).to_have_count(0)
        page.locator("#login-form [name=username]").fill("viewer")
        page.locator("#login-form [name=password]").fill("viewer-password")
        page.locator("#login-form button").click()
        page.wait_for_function(
            "document.getElementById('server-status')?.textContent==='Server Online'"
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
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(
            path=str(root / "work/semantic-mobile.png"),
            full_page=True,
            animations="disabled",
        )
        assert errors == []
        browser.close()
