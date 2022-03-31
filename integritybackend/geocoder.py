import geocoder
import logging


_logger = logging.getLogger(__name__)


class Geocoder:
    def reverse_geocode(self, lat, lon):
        """Retrieves reverse geocoding informatioon for the given latitude and longitude.

        Args:
            lat, long: latitude and longitude to reverse geocode, as floats

        Returns:
            geolocation JSON

        """
        # TODO: Add some kind of throttling and/or caching to prevent us from sending more than 1 req/sec.
        response = geocoder.osm([lat, lon], method="reverse")
        if response.status_code != 200 or response.status != "OK":
            _logger.error(
                "Reverse geocode lookup for (%s, %s) failed with: %s",
                lat,
                lon,
                response.status,
            )
            return None

        return self._json_to_address(response.json)

    def _json_to_address(self, geo_json):
        """Convert geocoding JSON to a uniform format for our own use."""
        if (osm_address := geo_json.get("raw", {}).get("address")) is None:
            _logger.warning("Reverse geocoding result did not include raw.address")
            return None
        address = {}
        address["country_code"] = osm_address.get("country_code")
        address["city"] = self._get_preferred_key(
            osm_address, ["city", "town", "municipality", "village"]
        )
        address["country"] = osm_address.get("country")
        address["state"] = self._get_preferred_key(
            osm_address, ["state", "region", "state_district"]
        )
        return address

    def _get_preferred_key(self, some_dict, keys):
        for key in keys:
            if key in some_dict:
                return some_dict.get(key)
        return None
