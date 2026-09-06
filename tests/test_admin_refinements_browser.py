from test_access import browser_headers
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
        return_value=[
            {'name':'chrony.service','startup':'enabled','status':'active / running'},
            {'name':'gpsd.service','startup':'disabled','status':'inactive / dead'},
            {'name':'ssh.service','startup':'enabled','status':'active / running'},
        ],
    ), patch("access_api.city_image", return_value=None):
        browser = p.chromium.launch(channel="msedge", headless=True, ignore_default_args=['--hide-scrollbars'])
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
                headers=browser_headers(response),
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
        expect(page.locator("#available-services input")).to_have_count(2)
        expect(page.locator("#monitored-services input")).to_have_count(1)
        expect(page.locator('#monitored-services .service-startup')).to_have_text('enabled')
        expect(page.locator('#monitored-services .service-current')).to_have_text('active / running')
        gps_row=page.locator('#available-services .service-choice').filter(has_text='gpsd.service')
        expect(gps_row.locator('.service-startup')).to_have_text('disabled')
        expect(gps_row.locator('.service-current')).to_have_text('inactive / dead')
        page.locator('#available-services input[value="gpsd.service"]').check()
        page.get_by_role("button", name="Monitor Selected Services", exact=True).click()
        page.locator('#monitored-services input[value="chrony.service"]').check()
        page.get_by_role(
            "button", name="Stop Monitoring Selected Services", exact=True
        ).click()
        page.get_by_role("button", name="Save Services", exact=True).click()
        expect(page.locator("#page-feedback")).to_have_text("Configuration saved.")
        assert m.get_settings()["settings"]["services"] == ["gpsd.service"]
        page.reload()
        expect(page.locator("#monitored-services")).to_contain_text("gpsd.service")
        expect(page.locator('#monitored-services .service-current')).to_have_text('inactive / dead')
        page.screenshot(
            path=str(root / "work/service-picker-54.png"),
            full_page=True,
            animations="disabled",
        )
        # Exercise real scrollbar widths; the small service fixture does not overflow.
        page.evaluate("""() => document.querySelectorAll('.service-list').forEach(list => {
            for(let i=0;i<35;i++)list.append(list.firstElementChild.cloneNode(true));
        })""")
        for width in [1440, 390]:
            page.set_viewport_size({'width':width,'height':1000})
            for theme in ['light','dark']:
                page.evaluate('(theme)=>document.documentElement.dataset.theme=theme',theme)
                for scroll in page.locator('.service-list-scroll').all():
                    assert scroll.evaluate('e=>e.scrollHeight>e.clientHeight')
                    colour=scroll.evaluate('e=>getComputedStyle(e).scrollbarColor')
                    assert colour != 'auto' and 'rgb(0, 0, 0)' not in colour
                    for header, field in [(2,'.service-startup'),(3,'.service-current')]:
                        h=scroll.locator('.service-list-heading span').nth(header-1).bounding_box()
                        cell=scroll.locator(field).first.bounding_box()
                        assert abs(h['x']+h['width']-cell['x']-cell['width'])<1
                    heading=scroll.locator('.service-list-heading')
                    before=heading.bounding_box()['y']
                    scroll.evaluate('e=>e.scrollTop=120')
                    assert abs(heading.bounding_box()['y']-before)<1
                    scroll.evaluate('e=>e.scrollTop=0')
                if width==1440:
                    page.screenshot(path=str(root/f'work/services-553-{theme}.png'),full_page=True,animations='disabled')
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
        page.get_by_role("button", name="New User", exact=True).click()
        expect(page.locator("#edit-user-dialog")).to_be_visible()
        expect(
            page.get_by_role("checkbox", name="Account Enabled", exact=True)
        ).not_to_be_checked()
        form = page.locator("#admin-user-form")
        for field in ['name','username','email','password']:
            required=page.locator('#admin-user-form [name='+field+']').locator('..')
            expect(required).to_have_class(__import__('re').compile('required'))
            assert required.locator('label').evaluate("e=>getComputedStyle(e,'::after').content") == '"*"'
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
