from pathlib import Path
from unittest.mock import patch
from playwright.sync_api import sync_playwright, expect
from test_access import system


def test_service_transfer_account_defaults_and_alignment(system):
    m, c = system
    m.save_settings(m.get_settings()["version"], {"services": ["chrony.service"]})
    root = Path(__file__).resolve().parents[1]
    with sync_playwright() as p, patch(
        "client_settings.system_services",
        return_value=["chrony.service", "gpsd.service", "ssh.service"],
    ), patch("access_api.city_image", return_value=None):
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        def route(route):
            r = route.request
            c.cookies.clear()
            response = c.request(
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
        page.locator("[name=username]").fill("admin")
        page.locator("[name=password]").fill("admin")
        page.locator("#login-form button").click()
        expect(page.locator("#system-cpu")).to_be_visible()
        page.locator("#world-panel>summary").click()
        summary = page.locator("#world-panel>summary").bounding_box()
        manage = page.locator(".world-manage").bounding_box()
        assert abs(summary["x"] + summary["width"] - manage["x"] - manage["width"]) < 2
        line = page.locator(".copyright-line").bounding_box()
        icon = page.locator(".github-link").bounding_box()
        assert abs(line["y"] + line["height"] / 2 - icon["y"] - icon["height"] / 2) < 2
        page.get_by_role("button", name="Administration", exact=True).click()
        for theme in ["light", "dark"]:
            page.evaluate(
                "(theme)=>document.documentElement.dataset.theme=theme", theme
            )
            for label in ["Roles & Permissions", "Service Health"]:
                item = page.get_by_role("link", name=label, exact=True)
                item.hover()
                assert item.evaluate("e=>getComputedStyle(e).color") not in [
                    "rgb(0, 0, 0)",
                    "rgba(0, 0, 0, 0.95)",
                ]
        page.get_by_role("link", name="Service Health", exact=True).click()
        expect(page.locator("#available-services option")).to_have_count(2)
        expect(page.locator("#monitored-services option")).to_have_count(1)
        page.locator("#available-services").select_option("gpsd.service")
        page.get_by_role("button", name="Monitor selected services", exact=True).click()
        page.locator("#monitored-services").select_option("chrony.service")
        page.get_by_role(
            "button", name="Stop monitoring selected services", exact=True
        ).click()
        page.get_by_role("button", name="Save Services", exact=True).click()
        expect(page.locator("#page-feedback")).to_have_text("Configuration saved.")
        assert m.get_settings()["settings"]["services"] == ["gpsd.service"]
        page.reload()
        expect(page.locator("#monitored-services")).to_contain_text("gpsd.service")
        page.screenshot(
            path=str(root / "work/service-picker-54.png"),
            full_page=True,
            animations="disabled",
        )
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.get_by_role("link", name="Roles & Permissions", exact=True).click()
        expect(
            page.get_by_role("heading", name="Configured Roles", exact=True)
        ).to_be_visible()
        expect(
            page.get_by_role("heading", name="Role Permissions", exact=True)
        ).to_be_visible()
        page.get_by_role("link", name="Users", exact=True).click()
        page.get_by_role("button", name="New user", exact=True).click()
        expect(page.locator("#edit-user-dialog")).to_be_visible()
        expect(
            page.get_by_role("checkbox", name="Account Enabled", exact=True)
        ).not_to_be_checked()
        form = page.locator("#admin-user-form")
        assert form.evaluate("e=>!e.checkValidity()")
        page.locator("#user-roles input[value=Administrator]").check()
        expect(page.locator("#user-roles input[value=User]")).not_to_be_checked()
        page.locator("#user-roles input[value=User]").check()
        expect(
            page.locator("#user-roles input[value=Administrator]")
        ).not_to_be_checked()
        for field, value in [
            ("name", "Test Person"),
            ("username", "new-person"),
            ("email", "person@example.test"),
            ("password", "test-password"),
        ]:
            page.locator("#admin-user-form [name=" + field + "]").fill(value)
        page.screenshot(path=str(root / "work/new-user-54.png"), animations="disabled")
        page.locator("#admin-user-form button").click()
        expect(page.locator("#page-feedback")).to_have_text("User saved.")
        expect(
            page.locator("#admin-users tr").filter(has_text="new-person")
        ).to_contain_text("Disabled")
        assert errors == []
        browser.close()
