from . import config
from .log_helper import LogHelper

import copy
import requests

_logger = LogHelper.getLogger()


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
        chains,
        nft_contract_address,
        testnet,
    ):
        """Registers an asset to the integrity blockchain.

        https://github.com/numbersprotocol/starling-requests/blob/main/CHANGELOG.md#misw-v110---2023-05-07
        https://docs.numbersprotocol.io/developers/commit-asset-history/commit-via-api

        Args:
            asset_name: name of the asset
            asset_description: description of the asset
            asset_cid: CID of the asset
            asset_sha256: SHA-256 of the asset
            asset_mime_type: MIME type of asset (use 'application/octet-stream' for encrypted assets)
            asset_timestamp_created: creation timestamp of the asset
            asset_extras: extra JSON object to be included in asset registration
            chains: List of chain names to register on: numbers, avalanche, near
            nft_contract_address: Avalanche contract address for minting an ERC-721 custody token for the asset; None to skip
            testnet: if testnet is used

        Returns:
            A dictionary mapping the chain name to the registration information.
            Failed registrations simply don't appear in the dictionary. So a total
            failure results in an empty dictionary being returned.
        """

        if not chains:
            raise TypeError("chains must be a non-zero length list")

        custom = copy.copy(asset_extras)
        custom.update({"name": asset_name})
        custom.update({"description": asset_description})

        if not nft_contract_address:
            registration_data = {
                "encodingFormat": asset_mime_type,
                "assetCid": asset_cid,
                "assetSha256": asset_sha256,
                "assetTimestampCreated": asset_timestamp_created,
                "custom": custom,
                "testnet": testnet,
                "assetCreator": "Starling Lab",
            }
        else:
            # nft_metadata = {
            #     "name": asset_name,
            #     "description": asset_description,
            #     "external_url": f"ipfs://{asset_cid}",
            #     "custom": custom,
            # }
            #
            # registration_data = [
            #     ("assetCid", asset_cid),
            #     ("assetSha256", asset_sha256),
            #     ("assetMimetype", asset_mime_type),
            #     ("assetTimestampCreated", asset_timestamp_created),
            #     ("custom", json.dumps(custom)),
            #     ("nftContractAddress", nft_contract_address),
            #     ("nftMetadata", json.dumps(nft_metadata)),
            # ]

            raise NotImplementedError("Don't know how to handle nft contract address")

        result = {}

        for chain in chains:
            if chain == "numbers":
                server = config.NUMBERS_NUMBERS_SERVER
            elif chain == "avalanche":
                server = config.NUMBERS_AVALANCHE_SERVER
            elif chain == "near":
                server = config.NUMBERS_NEAR_SERVER
            else:
                raise NotImplementedError(f"Unknown chain {chain}")

            resp = requests.post(
                server,
                headers={"Authorization": f"token {config.NUMBERS_API_KEY}"},
                json=registration_data,
            )

            if not resp.ok:
                _logger.error(
                    f"Numbers registration on {chain} failed: {resp.status_code} {resp.text}"
                )
                continue

            data = resp.json()
            if "error" in data:
                _logger.error(
                    f"Numbers registration on {chain} failed: {resp.status_code} {resp.text}"
                )
                continue

            _logger.info(f"Numbers registration on {chain} succeeded: {resp.text}")
            result[chain] = data

        return result

    @staticmethod
    def register_archive(
        asset_name,
        asset_description,
        asset_cid,
        asset_sha256,
        asset_mime_type,
        asset_timestamp_created,
        nft_contract_address,
        author,
        org_id,
        collection_id,
        extras,
        enc_zip_sha,
        enc_zip_md5,
        enc_zip_cid,
        content_sha,
        content_md5,
        content_cid,
        zip_sha,
        zip_md5,
        zip_cid,
        chains,
        testnet,
    ):
        """
        Registers an asset to the integrity blockchain.

        Similar to register(), but asset_extras is generated for you.
        """

        asset_extras = {
            "author": author,
            "usageInfo": "Encrypted with AES-256.",
            "keywords": [org_id, collection_id],
            "extras": extras,
            "contentFingerprints": [
                f"hash://sha256/{enc_zip_sha}",
                f"hash://md5/{enc_zip_md5}",
                f"ipfs://{enc_zip_cid}",
            ],
            "relatedContent": [
                {
                    "value": f"hash://sha256/{content_sha}",
                    "description": "The SHA-256 of the original content.",
                },
                {
                    "value": f"hash://md5/{content_md5}",
                    "description": "The MD5 of the original content.",
                },
                {
                    "value": f"ipfs://{content_cid}",
                    "description": "The CID of the original content.",
                },
                {
                    "value": f"hash://sha256/{zip_sha}",
                    "description": "The SHA-256 of the unencrypted archive.",
                },
                {
                    "value": f"hash://md5/{zip_md5}",
                    "description": "The MD5 of the unencrypted archive.",
                },
                {
                    "value": f"ipfs://{zip_cid}",
                    "description": "The CID of the unencrypted archive.",
                },
            ],
        }

        return Numbers.register(
            asset_name,
            asset_description,
            asset_cid,
            asset_sha256,
            asset_mime_type,
            asset_timestamp_created,
            asset_extras,
            chains,
            nft_contract_address,
            testnet,
        )
