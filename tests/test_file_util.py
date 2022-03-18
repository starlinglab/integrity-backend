import os
from .context import asset_helper
from .context import config
from .context import file_util

import pytest


def test_get_hash_from_filename():
    for filename in [
        "1a2s3d4f5g.jpg",
        "1a2s3d4f5g-meta.json",
        "/a/b/c/1a2s3d4f5g-meta.json",
        "1a2s3d4f5g-foobar.json",
    ]:
        assert file_util.FileUtil.get_hash_from_filename(filename) == "1a2s3d4f5g"


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


def test_get_collection_id_from_filename():
    assert (
        file_util.FileUtil.get_collection_id_from_filename(
            f"{config.INTERNAL_ASSET_STORE}/some-org/my-test-collection/some-file.jpg"
        )
        == "my-test-collection"
    )

    with pytest.raises(Exception) as exc_info:
        file_util.FileUtil.get_collection_id_from_filename("/very/bogus/nonono.jpg")
        assert "Could not extract collection" in exc_info.value
