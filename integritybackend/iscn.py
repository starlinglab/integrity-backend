from . import config
from .log_helper import LogHelper

import json
import requests

_logger = LogHelper.getLogger()
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
            iscnId if the registration succeeded; None otherwise
        """
        response = requests.post(_REGISTER, json={"metadata": registration})

        if not response.ok:
            _logger.error(
                f"ISCN registration failed: {response.status_code} {response.text}"
            )
            return None
        _logger.info(f"ISCN registration succeeded: {response.text}")
        return json.loads(response.text)["iscnId"]
