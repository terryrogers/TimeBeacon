from pathlib import Path
from unittest.mock import patch
from playwright.sync_api import sync_playwright, expect
from test_access import system
from test_avatars import photo_bytes


def test_client_palette_and_searchable_clock_navigation(system):
    m, client = system
    root = Path(__file__).resolve().parents[1]
    with sync_playwright() as p, patch("access_api.city_image", side_effect=lambda monitor,zone,city=None: {'image_url':'https://upload.wikimedia.org/test-clock.png'} if zone=='Asia/Kathmandu' else None):
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
        warmed_images=[]
        def clock_image(route):
            warmed_images.append(route.request.url)
            route.fulfill(status=200,content_type='image/png',headers={'Cache-Control':'public, max-age=3600'},body=photo_bytes())
        page.route('https://upload.wikimedia.org/test-clock.png',clock_image)
        page.goto("https://testserver/")
        page.locator("[name=username]").fill("admin")
        page.locator("[name=password]").fill("admin")
        page.locator("#login-form button").click()
        expect(page.locator(".brand-home")).to_have_attribute("href", "/")
        expect(page.locator(".github-link")).to_have_attribute(
            "href", "https://github.com/terryrogers/TimeBeacon"
        )
        expect(page.locator(".world-manage")).not_to_be_visible()
        page.locator("#world-panel > summary").click()
        expect(page.locator(".world-manage")).to_be_visible()
        page.get_by_role("link", name="Manage", exact=True).click()
        expect(page).to_have_url("https://testserver/user-settings#user-clocks")
        search = page.get_by_role("textbox", name="Search time zones and locations")
        search.fill("Kathmandu")
        item = page.locator('#clock-picker .item[data-value="Asia/Kathmandu"]')
        expect(item).to_be_visible()
        expect(item.locator(".flag")).to_have_class("np flag")
        expect(item.locator(".clock-picker-location")).to_contain_text("Kathmandu")
        page.screenshot(
            path=str(root / "work/clock-picker-53.png"),
            full_page=True,
            animations="disabled",
        )
        item.click()
        page.get_by_role("button", name="Add Clock", exact=True).click()
        expect(page.locator("#clock-feedback")).to_have_text(
            "Clock added to your account. City background ready."
        )
        assert warmed_images==['https://upload.wikimedia.org/test-clock.png']
        assert (
            page.locator("#clock-backgrounds").bounding_box()["y"]
            > page.locator("#clock-form").bounding_box()["y"]
        )
        page.get_by_role("link", name="Administration", exact=True).click()
        page.get_by_role("link", name="Time Clients", exact=True).click()
        expect(page.locator("#page-title")).to_have_text("Time Clients")
        expect(page.locator("textarea[name=services]")).to_have_count(0)
        page.locator('[aria-label="Healthy background colour"]').fill("#224466")
        page.locator('[aria-label="Healthy text colour"]').fill("#ffffff")
        page.locator("#client-colour-mode").check(force=True)
        expect(page.locator("#client-colour-mode-label")).to_have_text("Dark Mode")
        page.get_by_role("button", name="Save Client Settings", exact=True).click()
        expect(page.locator("#page-feedback")).to_have_text("Client settings saved.")
        page.screenshot(
            path=str(root / "work/client-settings-53.png"),
            full_page=True,
            animations="disabled",
        )
        page.reload()
        expect(page.locator("#client-colour-mode")).to_be_checked()
        page.get_by_role("link", name="Service Health", exact=True).click()
        expect(page.locator("[name=warning_seconds]")).to_have_count(0)
        page.locator(".brand").click()
        expect(page.locator("#system-cpu")).to_be_visible()
        page.locator("#clients-panel>summary").click()
        page.evaluate("document.documentElement.dataset.theme='dark'")
        expect(page.locator(".summary-card.ok")).to_have_css(
            "background-color", "rgb(34, 68, 102)"
        )
        expect(page.locator(".summary-card.ok")).to_have_css(
            "color", "rgb(255, 255, 255)"
        )
        page.evaluate("document.documentElement.dataset.theme='light'")
        expect(page.locator(".summary-card.ok")).not_to_have_css(
            "background-color", "rgb(34, 68, 102)"
        )
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        assert errors == []
        browser.close()
