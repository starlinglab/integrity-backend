import os
from .context import asset_helper
from .context import file_util

from zipfile import ZipFile

import pytest


def test_get_hash_from_filename():
    for filename in [
        "1a2s3d4f5g.jpg",
        "1a2s3d4f5g-meta.json",
        "/a/b/c/1a2s3d4f5g-meta.json",
        "1a2s3d4f5g-foobar.json",
    ]:
        assert file_util.FileUtil.get_hash_from_filename(filename) == "1a2s3d4f5g"


def test_make_zip(tmpdir):
    test_path = tmpdir.join("test.txt")
    test_path.write("some test data")

    more_test_path = tmpdir.join("more-test.txt")
    more_test_path.write("more test data")

    zip_path = tmpdir.join("output.zip")
    file_util.FileUtil.make_zip([test_path, more_test_path], zip_path)

    assert zip_path.check()
    with ZipFile(zip_path) as zipf:
        assert zipf.namelist().sort() == ["test.txt", "more-test.txt"].sort()


def test_get_organization_id_from_filename():
    organization_id = "my-test-organization-id"
    ah = asset_helper.AssetHelper(organization_id)
    filename = os.path.join(ah.dir_internal_create, "some-file.jpg")
    assert (
        file_util.FileUtil.get_organization_id_from_filename(filename)
        == organization_id
    )

    with pytest.raises(Exception) as exc_info:
        file_util.FileUtil.get_organization_id_from_filename("/very/bogus/nonono.jpg")
        assert "Could not extract organization" in exc_info.value
