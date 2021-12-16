import geocoder

class Geocoder:
    def reverse_geocode(self, lat, lon):
        """Retrieves reverse geocoding informatioon for the given latitude and longitude.

        Args:
            lat, long: latitude and longitude to reverse geocode, as floats

        Returns:
            geolocation JSON

        """
        # We shouldn't send more than 1 request per second. TODO: Add some kind of throttling and/or caching.
        response = geocoder.osm([lat, lon], method="reverse")
        # TODO: add error handling
        return response.json


