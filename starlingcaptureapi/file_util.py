from . import config
from hashlib import sha256

import errno
import logging
import os
import subprocess
import uuid

_logger = logging.getLogger(__name__)


class FileUtil:
    """Manages file system and file names."""

    def create_dir(self, dir_path):
        """Creates a new directory.

        Logs if the new directory was created or if it already existed.

        Args:
            dir_path: the local path to the new directory

        Raises:
            any errors that happened during directory creation
            (an already-existing directory is not considered an error)
        """
        try:
            os.makedirs(dir_path)
            _logger.info("Created directory %s", dir_path)
        except OSError as err:
            if err.errno == errno.EEXIST:
                _logger.info("Directory %s already exists", dir_path)
            else:
                raise err

    def generate_uuid(self):
        """Generates a randomly generated UUID.

        Returns:
            the UUID
        """
        return str(uuid.uuid4())

    def digest_sha256(self, file_path):
        """Generates SHA-256 digest of a file.

        Args:
            file_path: the local path to a file

        Returns:
            the HEX-encoded SHA-256 digest of the input file
        """
        hasher = sha256()
        with open(file_path, "rb") as f:
            # Parse file in blocks
            for byte_block in iter(lambda: f.read(4096), b""):
                hasher.update(byte_block)
            return hasher.hexdigest()
        # TODO: handle error (image not found, etc.)

    @staticmethod
    def digest_cidv1(self, file_path):
        """Generates the CIDv1 of a file, as determined by ipfs add.

        Args:
            file_path: the local path to a file

        Returns:
            CIDv1 in the canonical string format

        Raises:
            Exception if errors are encountered during processing
        """

        if not os.path.exists(os.path.expanduser("~/.ipfs")):
            proc = subprocess.run(
                ["ipfs", "init"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            if proc.returncode != 0:
                raise Exception(
                    f"'ipfs init' failed with code {proc.returncode} and output:\n\n{proc.stdout}"
                )

            _logger.info("Created IPFS repo since it didn't exist")

        proc = subprocess.run(
            [
                config.IPFS_BIN_PATH,
                "add",
                "--only-hash",
                "--cid-version=1",
                "-Q",
                file_path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        if proc.returncode != 0:
            raise Exception(
                f"'ipfs add --only-hash --cid-version=1' failed with code {proc.returncode} and output:\n\n{proc.stdout}"
            )

        return proc.stdout.strip()
