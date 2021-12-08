from .context import exif


def test_convert_latitude():
    exif_lat = exif.Exif().convert_latitude(-15.9321422)
    assert exif_lat == ("15/1 55/1 3920383475626017/70368744177664", "S")


def test_convert_longitude():
    exif_lon = exif.Exif().convert_longitude(-57.6317174)
    assert exif_lon == ("57/1 37/1 7625579331556737/140737488355328", "W")
