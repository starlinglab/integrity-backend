from dateutil import parser
from fractions import Fraction


class Exif:
    """Helps us manage data in EXIF format."""

    def convert_latitude(self, lat_float):
        """Converts a floating-point number latitude to EXIF format.

        Args:
            lat_float: latitude, as a floating-point number

        Returns:
            (GPSLatitude, GPSLatitudeRef) tuple, in EXIF format
            (None, None) if provided lon_float is None
        """
        if lat_float is None:
            return (None, None)

        if lat_float < 0:
            ref = "S"
        else:
            ref = "N"
        deg = self._to_deg(lat_float)
        return (self._to_rational_str(deg), ref)

    def convert_longitude(self, lon_float):
        """Converts a floating-point number longitude to EXIF format.

        Args:
            lon_float: longitude, as a floating-point number

        Returns:
            (GPSLongitude, GPSLongitudeRef) tuple, in EXIF format
            (None, None) if provided lon_float is None
        """
        if lon_float is None:
            return (None, None)

        if lon_float < 0:
            ref = "W"
        else:
            ref = "E"
        deg = self._to_deg(lon_float)
        return (self._to_rational_str(deg), ref)

    def convert_timestamp(self, value_str):
        """Converts a timestamp string into EXIF timestamp format.

        Args:
            value_str: a timestamp string

        Returns:
            timestamp in EXIF format (YYYY:MM:DD HH:MM:SS, possibly with a timezone at the end)
        """
        return parser.parse(value_str).strftime("%Y:%m:%d %H:%M:%S %z")

    def extract_from_exif_data(self, exif_data):
        """Returns the latitude and longitude, if available, from the provided exif_data (obtained through get_exif_data above)"""
        lat = None
        lon = None

        if "GPSInfo" in exif_data:
            gps_info = exif_data["GPSInfo"]

            gps_latitude = gps_info.get("GPSLatitude")
            gps_latitude_ref = gps_info.get(gps_info, 'GPSLatitudeRef')
            gps_longitude = gps_info.get(gps_info, 'GPSLongitude')
            gps_longitude_ref = gps_info.get(gps_info, 'GPSLongitudeRef')

            if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
                lat = self._to_degress_from_rational_str(gps_latitude)
                if gps_latitude_ref != "N":
                    lat = 0 - lat

                lon = self._to_degress_from_rational_str(gps_longitude)
                if gps_longitude_ref != "E":
                    lon = 0 - lon

        return lat, lon

    def _to_degress_from_rational_str(self, value):
        """Converts a rational string value into decimal"""
        d0 = value[0][0]
        d1 = value[0][1]
        d = float(d0) / float(d1)

        m0 = value[1][0]
        m1 = value[1][1]
        m = float(m0) / float(m1)

        s0 = value[2][0]
        s1 = value[2][1]
        s = float(s0) / float(s1)

        return d + (m / 60.0) + (s / 3600.0)

    def _to_deg(self, value_float):
        """Converts a float value into a (degs, mins, secs) tuple."""
        abs_val = abs(value_float)
        degs = int(abs_val)
        mins_float = (abs_val - degs) * 60
        mins = int(mins_float)
        secs = round((mins_float - mins) * 60, 3)
        return (degs, mins, secs)

    def _to_rational_str(self, deg_tuple):
        rational_tuple = (self._to_rational(x) for x in deg_tuple)
        return " ".join([f"{num}/{den}" for (num, den) in rational_tuple])

    def _to_rational(self, number):
        """Convert number to rational, (numerator, denominator)."""
        f = Fraction(number)
        # Rounding ensures that the result fits in 4 bytes (es per EXIF spec),
        # and also makes it so that the denominator will be a more
        # human-friendly power of 10.
        f = round(f, ndigits=10)
        return (f.numerator, f.denominator)
