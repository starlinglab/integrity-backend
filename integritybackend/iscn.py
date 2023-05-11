from typing import Union
from . import config
from .log_helper import LogHelper

import requests

_logger = LogHelper.getLogger()
_REGISTER = f"{config.ISCN_SERVER}/iscn/new/"


class Iscn:
    """Handles interactions with ISCN"""

    @staticmethod
    def register(registration: dict) -> Union[None, dict, list]:
        """Registers an asset on ISCN with the provided metadata.

        Args:
            registration: the complete contents of the ISCN registration; must comply with the
                ISCN schema (https://github.com/likecoin/iscn-specs/tree/master/schema)

        Returns:
            ISCN registration receipt if the registration succeeded; None otherwise
        """
        resp = requests.post(_REGISTER, json={"metadata": registration})

        if not resp.ok:
            _logger.error(f"ISCN registration failed: {resp.status_code} {resp.text}")
            return None

        _logger.info(f"ISCN registration succeeded: {resp.text}")
        return resp.json()

    @staticmethod
    def register_archive(
        enc_zip_sha,
        enc_zip_md5,
        enc_zip_cid,
        content_sha,
        content_md5,
        content_cid,
        zip_sha,
        zip_md5,
        zip_cid,
        name,
        description,
        author,
        keywords,
        date_created,
        record_notes,
    ) -> Union[None, dict, list]:
        """
        Register an archived asset on ISCN.

        A valid schema is generated using the provided params.

        Returns:
            ISCN registration receipt if the registration succeeded; None otherwise
        """

        return Iscn.register(
            {
                "contentFingerprints": [
                    f"hash://sha256/{enc_zip_sha}",
                    f"hash://md5/{enc_zip_md5}",
                    f"ipfs://{enc_zip_cid}",
                ],
                "stakeholders": [
                    {
                        "contributionType": "http://schema.org/citation",
                        "footprint": f"hash://sha256/{content_sha}",
                        "description": "The SHA-256 of the original content.",
                    },
                    {
                        "contributionType": "http://schema.org/citation",
                        "footprint": f"hash://md5/{content_md5}",
                        "description": "The MD5 of the original content.",
                    },
                    {
                        "contributionType": "http://schema.org/citation",
                        "footprint": f"ipfs://{content_cid}",
                        "description": "The CID of the original content.",
                    },
                    {
                        "contributionType": "http://schema.org/citation",
                        "footprint": f"hash://sha256/{zip_sha}",
                        "description": "The SHA-256 of the unencrypted archive.",
                    },
                    {
                        "contributionType": "http://schema.org/citation",
                        "footprint": f"hash://md5/{zip_md5}",
                        "description": "The MD5 of the unencrypted archive.",
                    },
                    {
                        "contributionType": "http://schema.org/citation",
                        "footprint": f"ipfs://{zip_cid}",
                        "description": "The CID of the unencrypted archive.",
                    },
                ],
                "type": "Record",
                "name": name,
                "description": description,
                "author": author,
                "usageInfo": "Encrypted with AES-256.",
                "keywords": keywords,
                "datePublished": date_created,
                "url": "",
                "recordNotes": record_notes,
            }
        )
