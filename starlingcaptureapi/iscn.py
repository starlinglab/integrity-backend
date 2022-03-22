from . import config

import logging
import requests

_logger = logging.getLogger(__name__)
_REGISTER = f"{config.ISCN_SERVER}/iscn/new/"


class Iscn:
    """Handles interactions with ISCN"""

    @staticmethod
    def register(registration: dict) -> bool:
        """Registers an asset on ISCN with the provided metadata.

        Args:
            registration: the complete contents of the ISCN registration; must comply with the
                ISCN schema (https://github.com/likecoin/iscn-specs/tree/master/schema)

        Returns:
            True if the registration succeeded; False otherwise
        """
        response = requests.post(_REGISTER, json={"metadata": registration})

        if not response.ok:
            _logger.error(
                "ISCN registration failed: %s %s", response.status_code, response.text
            )
            return False

        return True

    @classmethod
    def register_archive(encrypted_archive_path) -> bool:
        """Creates a registration record for this asset, signs it and registers it with ISCN.

        Args:
            encrypted_archive: the encrypted archive to register
                this archive gives us access to metadata, CIDs, file paths, etc

        Returns:
            True if the registration succeeded; False otherwise
        """
        # 1. Create registration record.
        #    See discussion in https://github.com/starlinglab/starling-integrity-api/issues/53
        #    for schema details. Might need to flesh out a few more details. Output of this step
        #    is some JSON.
        # 2. Sign registration record with authsign (Ana's note: I have no idea what this means, but it says so in Mural)
        # 3. Send registration records out:
        #    TODO: are we sending out the signed record? If not, where does this signed record go to?
        #    3.1. Send to ISCN, using `register` method above
        #    3.2. Send to Numbers. TODO: figure out what the endpoint for Numbers is, interface, etc.
        pass
