from file_util import FileUtil

import config
import json
import logging
import os
import subprocess

_logger = logging.getLogger(__name__)


class ClaimTool:
    """Manages interactions with the claim_tool binary."""


    def run(self, claim_dict, image_filename, output_dir):
        """Run claim_tool on the given filename with the provided claim.

        Args:
            claim_dict: a dictionary with the claim contents
            image_filename: full filename path to the image
            output_dir: path to put the image with embedded claim

        Returns:
            an integer with the return code from the claim_tool run
        """
        output_filename = os.path.join(config.IMAGES_DIR, output_dir, FileUtil().digest_sha256(image_filename) + ".jpg")
        _logger.info("Creating file at %s", output_dir)

        # TODO: Should the original image also be set as a parent?
        args = [
            config.CLAIM_TOOL_PATH,
            "-c",
            json.dumps(claim_dict),
            "-o",
            output_filename,
            "-p",
            image_filename
        ]
        popen = subprocess.Popen(args, stdout=subprocess.PIPE)
        popen.wait()
        if popen.returncode != 0:
            _logger.error("claim_tool returned code %d", popen.returncode)
            _logger.error("claim_tool output:\n %s", popen.stdout.read())

        return popen.returncode
