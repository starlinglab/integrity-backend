from .context import exif


def test_convert_latitude():
    exif_lat = exif.Exif().convert_latitude(-15.9321422)
    assert exif_lat == ("15/1 55/1 6964/125", "S")


def test_convert_longitude():
    exif_lon = exif.Exif().convert_longitude(-57.6317174)
    assert exif_lon == ("57/1 37/1 54183/1000", "W")

def test_convert_timestamp():
    exif_ts = exif.Exif().convert_timestamp("2021-10-30T18:43:14Z")
    assert exif_ts == "2021:10:30 18:43:14 +0000"
