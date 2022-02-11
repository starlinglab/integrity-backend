import pytest

from .context import asset_helper


def test_rejects_non_file_safe_org():
    with pytest.raises(ValueError, match="filename safe"):
        asset_helper.AssetHelper("not File Safe")


def test_directory_contains_org():
    helper = asset_helper.AssetHelper("hyphacoop")
    assert helper.get_claims_internal() == "/tests/assets_dir/hyphacoop/claims"
