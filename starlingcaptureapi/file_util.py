from . import config
from hashlib import sha256

import errno
import logging
import os
import uuid
import subprocess

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

    def register_timestamp(self, file_path, ts_file_path, timeout=5, min_cals=2):
        """Creates a opentimestamps file for the given file.

        Args:
            file_path: path to file
            ts_file_path: output path for opentimestamps file (.ots)
            timeout: Timeout before giving up on a calendar
            min_cals: timestamp is considered done if at least this many calendars replied

        Raises:
            any file I/O errors
            Exception if errors are encountered during processing
        """

        with open(file_path, "rb") as inp, open(ts_file_path, "wb") as out:
            proc = subprocess.run(
                [
                    config.OTS_CLIENT_PATH,
                    "stamp",
                    "--timeout",
                    str(timeout),
                    "-m",
                    str(min_cals),
                ],
                stdin=inp,  # Read file from stdin, so that output is on stdout
                stdout=out,  # Write output to given output file
                stderr=subprocess.PIPE,
            )

        if proc.returncode != 0:
            raise Exception(
                f"'ots stamp' failed with code {proc.returncode} and output:\n\n{proc.stderr.decode()}"
            )
