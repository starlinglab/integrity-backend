import pytest

from .context import config
from .context import asset_helper


def test_rejects_non_file_safe_org():
    with pytest.raises(ValueError, match="filename safe"):
        asset_helper.AssetHelper("not File Safe")
