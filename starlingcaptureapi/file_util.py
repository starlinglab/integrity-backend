from . import config

from hashlib import sha256

import errno
import logging
import os
import re
import uuid
import zipfile

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
    def get_hash_from_filename(filename: str) -> str:
        """Extracts the file hash from the given filename.

        Args:
            filename: the filename to process, which is expected to be shaped like:
                `<hash>-meta.json`
                `<hash>-signature.json`
                `<hash>.<ext>`

        Returns:
            the hash part of the filename
        """
        name, _ = os.path.splitext(os.path.basename(filename))
        return name.split("-")[0]

    @staticmethod
    def get_organization_id_from_filename(filename: str) -> str:
        """Extracts the organization id from the given filename.

        Args:
            filename: full filename to process, expected to be shaped like:
                ..../internal/organization_id/...some_filename.some_ext

        Returns:
            the extracted organization id

        Raises:
            Exception if couldn't find an organization id
        """
        match = re.search(f".*{config.INTERNAL_ASSET_STORE}\\/(.*?)\\/.*", filename)
        if match and len(match.groups()) > 0:
            return match.group(1)

        raise Exception(f"Could not extract organization id from filename {filename}")

    @staticmethod
    def make_zip(filenames: list[str], out_file: str):
        """Makes a zip file containing the given list of files.

        Args:
            filenames: list of full filenames to include in zip
            out_file: full path to output zip file
        """
        with zipfile.ZipFile(out_file, "w") as zipf:
            for filename in filenames:
                # This defaults to having an archive name that matches the given filename,
                # which preserve the entire directory structure.
                zipf.write(filename, compress_type=zipfile.ZIP_DEFLATED)
