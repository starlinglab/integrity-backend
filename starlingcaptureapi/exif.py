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
        return (f.numerator, f.denominator)


