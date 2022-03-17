from starlingcaptureapi.zip_util import extract_file
from .context import zip_util

from zipfile import ZipFile


def test_zip(tmpdir):

    # Test make_zip

    test_path = tmpdir.join("test.txt")
    test_path.write("some test data")

    more_test_path = tmpdir.join("more-test.txt")
    more_test_path.write("more test data")

    zip_path = tmpdir.join("output.zip")
    zip_util.make([test_path, more_test_path], zip_path, flat=True)

    assert zip_path.check()

    # Test listing

    assert zip_util.listing(zip_path).sort() == ["test.txt", "more-test.txt"].sort()

    # Test extract

    extracted_path = test_path + ".extract"
    zip_util.extract_file(zip_path, "test.txt", extracted_path)

    assert extracted_path.read() == test_path.read()

    # Test append

    more_test_append_path = "more_test_append.txt"
    zip_util.append(zip_path, more_test_path, more_test_append_path)

    assert more_test_append_path in zip_util.listing(zip_path)
