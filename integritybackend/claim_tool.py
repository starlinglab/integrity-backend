from . import config

import json
import logging
import subprocess

_logger = logging.getLogger(__name__)


class ClaimTool:
    """Manages interactions with the claim_tool binary."""

    def run_claim_inject(self, claim_dict, asset_fullpath, parent_asset_fullpath):
        """Overwrite the claim information an asset file with the provided claim, linked to a parent asset if provided.

        Args:
            claim_dict: a dictionary with the claim contents
            asset_fullpath: the local path to the asset file
            parent_asset_fullpath: local path to the parent asset file; or None

        Raises:
            Exception if something goes wrong with injection
        """
        if parent_asset_fullpath is None:
            args = [
                config.CLAIM_TOOL_PATH,
                "--claimdef",
                json.dumps(claim_dict),
                "--output",
                asset_fullpath,
            ]
        else:
            args = [
                config.CLAIM_TOOL_PATH,
                "--claimdef",
                json.dumps(claim_dict),
                "--output",
                asset_fullpath,
                "--parent",
                parent_asset_fullpath,
            ]
        popen = subprocess.Popen(args, stdout=subprocess.PIPE)
        popen.wait()
        if popen.returncode != 0:
            raise Exception(
                f"claim_tool failed with code {popen.returncode} and output: {popen.stdout.read()}"
            )

    def run_claim_dump(self, asset_fullpath, claim_fullpath):
        """Write claim information of an asset to a file.

        Args:
            asset_fullpath: the local path to the asset file
            claim_fullpath: the local path to write claim information

        Raises:
            Exception if errors are encountered
        """
        args = [
            config.CLAIM_TOOL_PATH,
            asset_fullpath,
            "--dump_store",
        ]
        with open(claim_fullpath, "w") as claim_file:
            popen = subprocess.Popen(args, stdout=claim_file)
            popen.wait()
            if popen.returncode != 0:
                raise Exception(
                    f"claim_tool failed with code {popen.returncode} and output: {popen.stdout.read()}"
                )
