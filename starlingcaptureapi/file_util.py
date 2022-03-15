from .crypto_util import AESCipher
from . import config

from Crypto.Cipher import AES
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

    def encrypt(self, key, file_path, enc_file_path):
        """Writes an encrypted version of the file to disk.

        Args:
            key: an AES-256 key as bytes (32 bytes)
            file_path: the path to the unencrypted file
            enc_file_path: the path where the encrypted file will go

        Raises:
            Any AES errors
            Any errors during file creation or I/O
        """

        cipher = AESCipher(key)

        # Read and encrypt 32 KiB at a time
        buffer_size = 32 * 1024

        with open(file_path, "rb") as dec, open(enc_file_path, "wb") as enc:
            # Begin file with the Initialization Vector.
            # This is a standard way of storing the IV in a file for AES-CBC,
            # and it's what the lit-js-sdk does.
            enc.write(cipher.iv)

            while True:
                data = dec.read(buffer_size)

                if len(data) % AES.block_size != 0 or len(data) == 0:
                    # This is the final block in the file
                    # It's not a multiple of the AES block size so it must be padded
                    enc.write(cipher.encrypt_last_block(data))
                    break

                enc.write(cipher.encrypt(data))

    def decrypt(self, key, file_path, dec_file_path):
        """Writes a decrypted version of the file to disk.

        Args:
            key: an AES-256 key as bytes (32 bytes)
            file_path: the path to the encrypted file
            dec_file_path: the path where the decrypted file will go

        Raises:
            Any AES errors
            Any errors during file creation or I/O
        """

        # Read and decrypt 16 KiB at a time
        buffer_size = 16 * 1024

        with open(file_path, "rb") as enc, open(dec_file_path, "wb") as dec:
            # Get IV
            iv = enc.read(16)
            cipher = AESCipher(key, iv)

            data = enc.read(buffer_size)
            while True:
                prev_data = data
                data = enc.read(buffer_size)

                if len(data) == 0:
                    # prev_data is the final block in the file and is therefore padded
                    dec.write(cipher.decrypt_last_block(prev_data))
                    break

                dec.write(cipher.decrypt(prev_data))

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
                config.IPFS_CLIENT_PATH,
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
