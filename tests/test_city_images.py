from unittest.mock import patch
from test_access import system, login, change
from security import IdentityStore
from city_images import city_image, fetch_city_image


def test_personal_toggle_and_photo_permissions(system):
    m, c = system
    login(c)
    assert c.get("/user/profile").json()["clock_backgrounds"] is True
    version = c.get("/dashboard/settings").json()["version"]
    change(
        c,
        "/administration/users",
        dict(username="viewer", password="viewer-password", roles=["User"]),
    )
    with patch("access_api.city_image", return_value={"city": "London"}) as photo:
        assert (
            c.get("/dashboard/clocks/image?zone=Europe/London").json()["image"]["city"]
            == "London"
        )
        assert (
            c.get("/dashboard/clocks/image?zone=Invalid/Unconfigured").status_code
            == 404
        )
        assert (
            c.put("/user/clock-backgrounds", json={"enabled": False}).status_code == 403
        )
        assert (
            change(c, "/user/clock-backgrounds", {"enabled": False}).status_code == 200
        )
        assert c.get("/dashboard/settings").json()["version"] > version
        photo.reset_mock()
        assert (
            c.get("/dashboard/clocks/image?zone=Europe/London").json()["image"] is None
        )
        photo.assert_not_called()
    IdentityStore(m).initialise()
    assert c.get("/user/profile").json()["clock_backgrounds"] is False
    login(c, "viewer", "viewer-password")
    assert c.get("/user/profile").json()["clock_backgrounds"] is True
    assert c.get("/dashboard/clocks/image?zone=Europe/London").status_code == 404


def test_image_cache_and_unavailable_images(system):
    m, _ = system
    with patch(
        "city_images.fetch_city_image", return_value={"city": "London"}
    ) as fetch:
        assert city_image(m, "Europe/London", "London") == {"city": "London"}
        assert city_image(m, "Europe/London", "London") == {"city": "London"}
        fetch.assert_called_once()
    with patch("city_images.fetch_city_image", side_effect=OSError("offline")) as fetch:
        assert city_image(m, "Asia/Tokyo") is None
        assert city_image(m, "Asia/Tokyo") is None
        fetch.assert_called_once()


def test_wikimedia_validation_and_attribution():
    page = {
        "title": "Tel Aviv",
        "coordinates": [{}],
        "pageimage": "Tel Aviv.jpg",
        "thumbnail": {
            "source": "https://upload.wikimedia.org/city.jpg?tracking=removed"
        },
    }
    metadata = {
        "Artist": {"value": '<a href="example">Photographer</a>'},
        "LicenseShortName": {"value": "CC BY-SA 4.0"},
        "Credit": {"value": "Own work"},
    }

    def response(params):
        return {"query": {"pages": [params]}}

    with patch(
        "city_images.request_json",
        side_effect=[
            response(page),
            response({"imageinfo": [{"extmetadata": metadata}]}),
        ],
    ) as query:
        result = fetch_city_image("Asia/Jerusalem", "Tel Aviv")
        assert query.call_args_list[0].args[1]["titles"] == "Tel Aviv"
        assert result["artist"] == "Photographer" and result["image_url"].endswith(
            "city.jpg"
        )
        assert result["license"] == "CC BY-SA 4.0"
    with patch(
        "city_images.request_json",
        return_value=response(
            {**page, "thumbnail": {"source": "http://localhost/private"}}
        ),
    ):
        assert fetch_city_image("Europe/London") is None
    with patch("city_images.request_json") as query:
        assert fetch_city_image("UTC") is None
        query.assert_not_called()
