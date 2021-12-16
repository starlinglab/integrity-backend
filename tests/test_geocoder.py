from unittest.mock import MagicMock

from .context import geocoder


def test_reverse_geocode(mocker):
    mocker.patch(
        "geocoder.osm",
        lambda *_, **kwargs: MagicMock(
            json={
                "raw": {
                    "address": {
                        "city": "Toronto",
                        "state": "Ontario",
                        "country": "Canada",
                        "country_code": "ca",
                    }
                }
            }
        ),
    )
    assert geocoder.Geocoder().reverse_geocode(1, 2) == {
        "city": "Toronto",
        "state": "Ontario",
        "country": "Canada",
        "country_code": "ca",
    }


def test_reverse_geocode_with_town(mocker):
    mocker.patch(
        "geocoder.osm",
        lambda *_, **kwargs: MagicMock(
            json={
                "raw": {
                    "address": {
                        "town": "Some Town",
                        "state": "Ontario",
                        "country": "Canada",
                        "country_code": "ca",
                    }
                }
            }
        ),
    )
    assert geocoder.Geocoder().reverse_geocode(1, 2) == {
        "city": "Some Town",
        "state": "Ontario",
        "country": "Canada",
        "country_code": "ca",
    }


def test_reverse_geocode_with_no_response(mocker):
    mocker.patch("geocoder.osm", lambda *_, **kwargs: MagicMock(json={}))
    assert geocoder.Geocoder().reverse_geocode(1, 2) == None
