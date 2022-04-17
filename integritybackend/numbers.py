from . import config
from .file_util import FileUtil
from .log_helper import LogHelper

import json
import magic
import os
import requests
import sys

from integritybackend import file_util

from datetime import datetime
from eth_account.datastructures import SignedMessage
from eth_account.messages import encode_defunct
from web3.auto import w3

_logger = LogHelper.getLogger()
_COMMIT_URL = config.NUMBERS_API_URL + "/commit"
_STARLINGMINTNFT_URL = config.NUMBERS_API_URL + "/starlingmintnft"


class Numbers:
    """Handles interactions with Numbers Protocol."""
    @staticmethod
    def get_ipfs_cid(filepath):
        file_util = FileUtil()
        return file_util.digest_cidv1(filepath)

    @staticmethod
    def sign_message(message: str, private_key: str):
        """Sign the message and create Ethereum-compatible signature

        Args:
            message (str): the message to be signed
            private_key (str): the Ethereum private key used to generate the signature

        Returns:
            str: the generate signature hexstr with 0x prefix
        """
        private_key_bytes = w3.toBytes(hexstr=private_key)
        encoded_message = encode_defunct(text=message)
        print(f'encoded message: {encoded_message}')
        signed_message: SignedMessage = w3.eth.account.sign_message(encoded_message, private_key=private_key_bytes)
        return signed_message.signature.hex()

    @staticmethod
    def verify_message(message: str, signature: str) -> str:
        """Verify Ethereum-compatible signature

        Args:
            message (str): the signed message
            signature (str): the signature generated from the signed message

        Returns:
            str: the recovered Ethereum wallet address
        """
        encoded_message = encode_defunct(text=message)
        return w3.eth.account.recover_message(encoded_message, signature=signature)

    @staticmethod
    def mint_nft(receiver_address, nft_metadata, blockchain_name='avalanche'):
        """Mint NFT on the integrity blockchain.

        https://github.com/numbersprotocol/enterprise-service/wiki/Web-3.0-API#nit-commit

        Args:
            receiver_address: mint NFT to the receiver's wallet address
            nft_metadata: ERC-721 NFT metadata in JSON format
            blockchain_name: mint NFT on the specified blockchain

        Raises:
            any file I/O errors
            JSON decoding errors

        Returns:
            NFT token URI and ID. If registration fails it returns None.
        """
        r = requests.post(
            _STARLINGMINTNFT_URL,
            headers={"Authorization": f"Bearer {config.NUMBERS_API_KEY}"},
            data=[
                ("address", receiver_address),
                ("json", json.dumps(nft_metadata)),
                ("blockchain_name", blockchain_name),
            ],
        )

        if not r.ok:
            _logger.error("Numbers starlingmintnft failed: %s %s", r.status_code, r.text)
            return None

        data = r.json()

        if data.get("response") is None:
            _logger.warning(
                "Numbers starlingmintnft response did not have the 'response' field: %s", r.text
            )
            return None
        if data["response"].get("tokenURI") is None:
            _logger.warning(
                "Numbers starlingmintnft response did not have the 'tokenURI' field: %s", r.text
            )
            return None
        if data["response"].get("tokenId") is None:
            _logger.warning(
                "Numbers starlingmintnft response did not have the 'tokenId' field: %s", r.text
            )
            return None

        return {
            'network': blockchain_name,
            'contractAddress': '0x4Dc5FD335fbC5614b2A1641c8A9F7e4b7cC80AE2',
            'tokenUri': data["response"]["tokenURI"],
            'tokenId': data["response"]["tokenId"],
        }

    @staticmethod
    def create_asset_tree(asset_filepath,
                          asset_creator_filepath,
                          nft_record_filepath='',
                          abstract=''):
        file_util = FileUtil()
        asset_tree = {}
        asset_tree['assetCid'] = file_util.digest_cidv1(asset_filepath),
        asset_tree['assetSha256'] = file_util.digest_sha256(asset_filepath)
        asset_tree['assetCreator'] = file_util.digest_cidv1(asset_creator_filepath)
        asset_tree['assetTimestampCreated'] = int(os.path.getctime(asset_filepath))
        asset_tree['license'] = {
            'name': 'mit',
            'document': 'https://opensource.org/licenses/MIT'
        }
        asset_tree['nftRecord'] = file_util.digest_cidv1(nft_record_filepath)
        # TODO: please set integrity CID, sha256sum, Ethereum signature if available
        #asset_tree['integrityCid'] =
        #asset_tree['integritySha256'] =
        #asset_tree['integritySignature'] =
        asset_tree['abstract'] = abstract
        asset_tree['encodingFormat'] = magic.Magic(mime=True).from_file(asset_filepath)
        return asset_tree

    @staticmethod
    def commit(asset,
               asset_tree,
               author,
               action,
               abstract,
               create_signature=False,
               private_key=''):
        """Registers a commit to the integrity blockchain.

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
        file_util = FileUtil()
        asset_cid = file_util.digest_cidv1(asset)
        asset_tree_cid = file_util.digest_cidv1(asset_tree)
        asset_tree_sha256 = file_util.digest_sha256(asset_tree)
        author_cid = file_util.digest_cidv1(author)
        action_cid = file_util.digest_cidv1(action)
        action_result_uri = f'https://{asset_tree_cid}.ipfs.dweb.link/'

        if create_signature:
            asset_tree_signature = Numbers.sign_message(asset_tree_sha256, private_key)
        else:
            asset_tree_signature = ""

        r = requests.post(
            _COMMIT_URL,
            headers={"Authorization": f"Bearer {config.NUMBERS_API_KEY}"},
            data=[
                ("assetCid", asset_cid),
                ("assetTreeCid", asset_tree_cid),
                ("assetTreeSha256", asset_tree_sha256),
                ("assetTreeSignature", asset_tree_signature),
                ("author", author_cid),
                ("action", action_cid),
                ("actionResultUri", action_result_uri),
                ("abstract", abstract),
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
