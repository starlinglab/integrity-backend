from . import config
from .log_helper import LogHelper

import json
import subprocess

_logger = LogHelper.getLogger()


class C2patool:
    """Manages interactions with the c2patool binary."""

    def run_claim_inject(
        self, claims: dict, input_path: str, output_path: str, parent_path: str = None
    ):
        """
        Inject C2PA claims into an asset, optionally inheriting claims from a parent asset.

        The output file will be overwritten if it already exists.

        Args:
            claims: a dictionary with the claim contents
            input_path: the local path to the input asset file
            output_path: the local path to the output asset file
            parent_path: local path to the parent asset file, or None (default)

        Raises:
            Exception if something goes wrong with injection
        """
        if parent_path is None:
            args = [
                config.C2PA_TOOL_PATH,
                input_path,
                "--config",
                json.dumps(claims),
                "--force",
                "--output",
                output_path,
            ]
        else:
            args = [
                config.C2PA_TOOL_PATH,
                input_path,
                "--config",
                json.dumps(claims),
                "--parent",
                parent_path,
                "--force",
                "--output",
                output_path,
            ]
        popen = subprocess.Popen(args, stdout=subprocess.PIPE)
        popen.wait()
        if popen.returncode != 0:
            raise Exception(
                f"c2patool failed with code {popen.returncode} and output: {popen.stdout.read()}"
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
            config.C2PA_TOOL_PATH,
            asset_fullpath,
        ]
        with open(claim_fullpath, "w") as claim_file:
            popen = subprocess.Popen(args, stdout=claim_file)
            popen.wait()
            if popen.returncode != 0:
                raise Exception(
                    f"c2patool failed with code {popen.returncode} and output: {popen.stdout.read()}"
                )
