import pytest


@pytest.fixture
def reverse_geocode_mocker(mocker):
    def patch(return_value):
        mocker.patch(
            "integritybackend.geocoder.Geocoder.reverse_geocode",
            lambda *_: return_value,
        )

    return patch
