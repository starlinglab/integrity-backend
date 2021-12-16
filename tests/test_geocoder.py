from unittest.mock import MagicMock

from .context import geocoder


def mock_osm_response(json={}, status_code=200, status="OK"):
    """Helper to make mock OSM responses for testing."""
    return lambda *_, **kwargs: MagicMock(
        json=json, status_code=status_code, status=status
    )


def test_reverse_geocode(mocker):
    mocker.patch(
        "geocoder.osm",
        mock_osm_response(
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
        mock_osm_response(
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
    mocker.patch("geocoder.osm", mock_osm_response(json={}))
    assert geocoder.Geocoder().reverse_geocode(1, 2) == None

    mocker.patch("geocoder.osm", mock_osm_response(status="ERROR - No results found"))
    assert geocoder.Geocoder().reverse_geocode(1, 2) == None
