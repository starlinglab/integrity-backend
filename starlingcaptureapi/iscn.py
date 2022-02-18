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
