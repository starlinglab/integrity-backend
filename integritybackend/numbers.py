from . import config
from .file_util import FileUtil

import logging
import requests

_logger = logging.getLogger(__name__)

file_util = FileUtil()

_COMMIT_URL_MAINNET = "https://node.numbersprotocol.io/api/1.1/wf/commit"
_COMMIT_URL_TESTNET = "https://node.numbersprotocol.io/version-test/api/1.1/wf/commit"
if (config.NUMBERS_API_NETWORK == "main"):
    _COMMIT_URL = _COMMIT_URL_MAINNET
elif (config.NUMBERS_API_NETWORK == "test"):
    _COMMIT_URL = _COMMIT_URL_TESTNET
else:
    raise Exception(
        f"Unknown Numbers Network {config.NUMBERS_API_NETWORK}"
    )


def commit(asset, asset_tree, author):
    """Register a commit to the integrity blockchain.

    https://github.com/numbersprotocol/enterprise-service/wiki/Web-3.0-API#nit-commit

    Args:
        asset: path to the asset file
        asset_tree: path to asset JSON
        author: path to author JSON

    Raises:
        any file I/O errors
        JSON decoding errors

    Returns:
        Transaction hash string. If registration fails it returns None.
    """

    asset_cid = file_util.digest_cidv1(asset)
    asset_tree_cid = file_util.digest_cidv1(asset_tree)
    asset_tree_sha = file_util.digest_sha256(asset_tree)
    author_cid = file_util.digest_cidv1(author)

    r = requests.post(
        _COMMIT_URL,
        headers={"Authorization", f"Bearer {config.NUMBERS_API_KEY}"},
        files=[
            ("assetCid", asset_cid),
            ("assetTreeCid", asset_tree_cid),
            ("assetTreeSha256", asset_tree_sha),
            ("author", author_cid),
            ("action", "testAction"),  # Will change in the future!
            ("actionResult", "testActionResult"),  # Will change in the future!
            ("dryRun", "false"),
            ("mockup", "false"),
        ],
    )

    if not r.ok:
        _logger.error("Numbers commit failed: %s %s", r.status_code, r.text)
        return None

    data = r.json()

    if data.get("response") is None:
        _logger.warning(
            "Numbers commit response did not have the 'response' field: %s", r.text
        )
        return None
    if data["response"].get("txHash") is None:
        _logger.warning(
            "Numbers commit response did not have the 'txHash' field: %s", r.text
        )
        return None

    return data["response"]["txHash"]
