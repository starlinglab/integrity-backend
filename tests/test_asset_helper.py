import pytest

from .context import config
from .context import asset_helper


def test_rejects_non_file_safe_org():
    with pytest.raises(ValueError, match="filename safe"):
        asset_helper.AssetHelper("not File Safe")


def test_path_for(monkeypatch, tmp_path):
    helper = asset_helper.AssetHelper("some-org")
    assert helper.path_for_action("my-collection", "c2pa-update").endswith(
        "/assets_dir/some-org/my-collection/action-c2pa-update"
    )
    assert helper.path_for_action_output("my-collection", "c2pa-update").endswith(
        "/shared_dir/some-org/my-collection/action-c2pa-update"
    )
