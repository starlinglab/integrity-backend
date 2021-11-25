import config

import json
import logging
import subprocess

_logger = logging.getLogger(__name__)


class ClaimTool:
    """Manages interactions with the claim_tool binary."""


    def run(self, claim_dict, image_filename):
        """Run claim_tool on the given filename with the provided claim.

        Args:
            claim_dict: a dictionary with the claim contents
            image_filename: full filename path to the image

        Returns:
            an integer with the return code from the claim_tool run
        """
        # TODO: Should the original image also be set as a parent?
        args = [
            config.CLAIM_TOOL_PATH,
            "-c",
            json.dumps(claim_dict),
            "-o",
            image_filename,
        ]
        popen = subprocess.Popen(args, stdout=subprocess.PIPE)
        popen.wait()
        if popen.returncode != 0:
            _logger.error("claim_tool returned code %d", popen.returncode)
            _logger.error("claim_tool output:\n %s", popen.stdout.read())

        return popen.returncode
