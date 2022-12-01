from . import config
from .log_helper import LogHelper

import copy
import json
import requests

_logger = LogHelper.getLogger()
_REGISTER = config.NUMBERS_API_URL


class Numbers:
    """Handles interactions with Numbers Protocol."""

    @staticmethod
    def register(
        asset_name,
        asset_description,
        asset_cid,
        asset_sha256,
        asset_mime_type,
        asset_timestamp_created,
        asset_extras,
        nft_contract_address,
    ):
        """Registers an asset to the integrity blockchain.

        https://github.com/numbersprotocol/enterprise-service/wiki/7.-Nit,-Native-Protocol-Tool#nit-create-asset

        Args:
            asset_name: name of the asset
            asset_description: description of the asset
            asset_cid: CID of the asset
            asset_sha256: SHA-256 of the asset
            asset_mime_type: MIME type of asset (use 'application/octet-stream' for encrypted assets)
            asset_timestamp_created: creation timestamp of the asset
            asset_extras: extra JSON object to be included in asset registration
            nft_contract_address: Avalanche contract address for minting an ERC-721 custody token for the asset; None to skip

        Returns:
            Numbers registration receipt if the registration succeeded; None otherwise
        """
        custom = copy.copy(asset_extras)
        custom.update({"name": asset_name})
        custom.update({"description": asset_description})

        if not nft_contract_address:
            registration_data = [
                ("assetCid", asset_cid),
                ("assetSha256", asset_sha256),
                ("assetMimetype", asset_mime_type),
                ("assetTimestampCreated", asset_timestamp_created),
                ("custom", json.dumps(custom)),
            ]
        else:
            nft_metadata = {
                "name": asset_name,
                "description": asset_description,
                "external_url": f"ipfs://{asset_cid}",
                "custom": custom,
            }

            registration_data = [
                ("assetCid", asset_cid),
                ("assetSha256", asset_sha256),
                ("assetMimetype", asset_mime_type),
                ("assetTimestampCreated", asset_timestamp_created),
                ("custom", json.dumps(custom)),
                ("nftContractAddress", nft_contract_address),
                ("nftMetadata", json.dumps(nft_metadata)),
            ]

        resp = requests.post(
            _REGISTER,
            headers={"Authorization": f"Bearer {config.NUMBERS_API_KEY}"},
            data=registration_data,
        )

        if not resp.ok:
            _logger.error(
                f"Numbers registration failed: {resp.status_code} {resp.text}"
            )
            return None

        data = resp.json()
        if data.get("response") is None:
            _logger.warning(
                "Numbers registration response did not have the 'response' field: %s",
                resp.text,
            )
            return None
        if data.get("status") != "success":
            _logger.warning(
                "Numbers registration didn't have success status: %s", resp.text
            )
            return None

        _logger.info(f"Numbers registration succeeded: {resp.text}")
        return data["response"]
