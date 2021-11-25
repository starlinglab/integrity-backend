import config

import json
import logging
import subprocess

_logger = logging.getLogger(__name__)

class ClaimTool:
    def run(self, claim_dict, image_filename):
        # TODO: Should the original image also be set as a parent?
        args = [
            config.CLAIM_TOOL_PATH,
            "-c",
            json.dumps(claim_dict),
            "-o",
            image_filename
        ]
        popen = subprocess.Popen(args, stdout=subprocess.PIPE)
        popen.wait()
        if popen.returncode != 0:
            _logger.error("claim_tool returned code %d", popen.returncode)
            _logger.error("claim_tool output:\n %s", popen.stdout.read())

        return popen.returncode
