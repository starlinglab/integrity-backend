import pytest


@pytest.fixture
def reverse_geocode_mocker(mocker):
    def patch(return_value):
        mocker.patch(
            "starlingcaptureapi.geocoder.Geocoder.reverse_geocode",
            lambda *_: return_value,
        )

    return patch
