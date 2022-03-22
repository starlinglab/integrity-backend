from .context import zip_util
from pathlib import Path


def test_make_zip(tmp_path):
    test_path = tmp_path / "test.txt"
    test_path.write_text("some test data")

    more_test_path = tmp_path / "more-test.txt"
    more_test_path.write_text("more test data")

    zip_path = tmp_path / "output.zip"
    zip_util.make([test_path, more_test_path], zip_path, flat=True)

    assert zip_path.exists()


def test_zip_listing(tmp_path):
    test_make_zip(tmp_path)
    zip_path = tmp_path / "output.zip"
    assert zip_util.listing(zip_path).sort() == ["test.txt", "more-test.txt"].sort()


def test_zip_extract(tmp_path):
    test_make_zip(tmp_path)

    zip_path = tmp_path / "output.zip"
    test_path = tmp_path / "test.txt"
    extracted_path = Path(str(test_path) + ".extract")

    zip_util.extract_file(zip_path, "test.txt", extracted_path)
    assert extracted_path.read_text() == test_path.read_text()


def test_zip_append(tmp_path):
    test_make_zip(tmp_path)

    zip_path = tmp_path / "output.zip"
    more_test_path = tmp_path / "more-test.txt"
    more_test_append_path = "more_test_append.txt"

    zip_util.append(zip_path, more_test_path, more_test_append_path)
    assert more_test_append_path in zip_util.listing(zip_path)
