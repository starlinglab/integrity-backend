from file_util import FileUtil
from asset_helper import AssetHelper

import config
import json
import logging
import os
import shutil
import subprocess

_asset_helper = AssetHelper()
_logger = logging.getLogger(__name__)


class ClaimTool:
    """Manages interactions with the claim_tool binary."""


    def run(self, claim_dict, asset_fullpath):
        """Run claim_tool on the given filename with the provided claim.

        Args:
            claim_dict: a dictionary with the claim contents
            asset_fullpath: the local path to the asset file

        Returns:
            an integer with the return code from the claim_tool run
        """
        tmp_file = _asset_helper.get_tmp_file_fullpath(".jpg")

        # TODO: Should the original image also be set as a parent?
        args = [
            config.CLAIM_TOOL_PATH,
            "-c",
            json.dumps(claim_dict),
            "-o",
            tmp_file,
            "-p",
            asset_fullpath
        ]
        popen = subprocess.Popen(args, stdout=subprocess.PIPE)
        popen.wait()
        if popen.returncode != 0:
            _logger.error("claim_tool returned code %d", popen.returncode)
            _logger.error("claim_tool output:\n %s", popen.stdout.read())
        else:
            # Copy the C2PA-injected asset to both the internal and shared asset directories.
            internal_file = _asset_helper.get_internal_file_fullpath(tmp_file)
            shutil.move(tmp_file, internal_file)
            shutil.copy2(internal_file, _asset_helper.get_assets_shared())
            _logger.info("New file added to the internal and shared assets directories: " + internal_file)

        return popen.returncode
