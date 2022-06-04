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
            ISCN registration receipt if the registration succeeded; None otherwise
        """
        resp = requests.post(_REGISTER, json={"metadata": registration})

        if not resp.ok:
            _logger.error(f"ISCN registration failed: {resp.status_code} {resp.text}")
            return None

        _logger.info(f"ISCN registration succeeded: {resp.text}")
        return resp.json()
