from .config import C2PA_CERT_STORE, C2PATOOL_PATH
from .log_helper import LogHelper

import json
import subprocess
import os

_logger = LogHelper.getLogger()


class C2patool:
    """Manages interactions with the c2patool binary."""

    def run_claim_inject(
        self,
        claims: dict,
        input_path: str,
        output_path: str,
        cert_name: str,
        key_name: str,
        algo: str,
        parent_path: str = None,
    ):
        """
        Inject C2PA claims into an asset, optionally inheriting claims from a parent asset.

        The output file will be overwritten if it already exists.

        Args:
            claims: a dictionary with the claim contents
            input_path: the local path to the input asset file
            output_path: the local path to the output asset file
            parent_path: local path to the parent asset file, or None (default)
            cert_name: name of C2PA cert file from org config
            key_name: name of C2PA priv key file from org config
            algo: C2PA cert algo, one of: ps256, ps384, ps512, es256, es384, es512, ed25519

        Raises:
            Exception if something goes wrong with injection
        """

        claims["alg"] = algo

        with open(os.path.join(C2PA_CERT_STORE, cert_name), "r") as f:
            cert_text = f.read()
        with open(os.path.join(C2PA_CERT_STORE, key_name), "r") as f:
            key_text = f.read()

        if parent_path is None:
            args = [
                C2PATOOL_PATH,
                input_path,
                "--config",
                json.dumps(claims),
                "--force",
                "--output",
                output_path,
            ]
        else:
            args = [
                C2PATOOL_PATH,
                input_path,
                "--config",
                json.dumps(claims),
                "--parent",
                parent_path,
                "--force",
                "--output",
                output_path,
            ]

        popen = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            env={"C2PA_PRIVATE_KEY": key_text, "C2PA_SIGN_CERT": cert_text},
        )
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
            C2PATOOL_PATH,
            asset_fullpath,
        ]
        with open(claim_fullpath, "w") as claim_file:
            popen = subprocess.Popen(args, stdout=claim_file)
            popen.wait()
            if popen.returncode != 0:
                raise Exception(
                    f"c2patool failed with code {popen.returncode} and output: {popen.stdout.read()}"
                )
