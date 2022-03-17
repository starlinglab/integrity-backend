from . import config
from .crypto_util import AESCipher

from Crypto.Cipher import AES
from hashlib import sha256, md5

import errno
import logging
import os
import subprocess
import uuid

_logger = logging.getLogger(__name__)


BUFFER_SIZE = 32 * 1024  # 32 KiB


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

    def digest(self, algo, file_path):
        """Generates cryptographic hash digest of a file.

        Args:
            algo: A string representing the hash algorithm. ("sha256", "md5")
            file_path: the local path to a file

        Returns:
            the HEX-encoded digest of the input file

        Raises:
            any file I/O errors
            NotImplementedError for an unknown hash algo
        """

        if algo == "sha256":
            hasher = sha256()
        elif algo == "md5":
            hasher = md5()
        else:
            raise NotImplementedError(f"unknown hash algo {algo}")

        with open(file_path, "rb") as f:
            # Parse file in blocks
            for byte_block in iter(lambda: f.read(BUFFER_SIZE), b""):
                hasher.update(byte_block)
            return hasher.hexdigest()

    def digest_sha256(self, file_path):
        """Generates SHA-256 digest of a file.

        Args:
            file_path: the local path to a file

        Returns:
            the HEX-encoded SHA-256 digest of the input file

        Raises:
            any file I/O errors
        """

        return self.digest("sha256", file_path)

    def digest_md5(self, file_path):
        """Generates MD5 digest of a file.

        Args:
            file_path: the local path to a file

        Returns:
            the HEX-encoded MD5 digest of the input file

        Raises:
            any file I/O errors
        """

        return self.digest("md5", file_path)

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

        with open(file_path, "rb") as dec, open(enc_file_path, "wb") as enc:
            # Begin file with the Initialization Vector.
            # This is a standard way of storing the IV in a file for AES-CBC,
            # and it's what the lit-js-sdk does.
            enc.write(cipher.iv)

            while True:
                data = dec.read(BUFFER_SIZE)

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

        with open(file_path, "rb") as enc, open(dec_file_path, "wb") as dec:
            # Get IV
            iv = enc.read(16)
            cipher = AESCipher(key, iv)

            data = enc.read(int(BUFFER_SIZE / 2))
            while True:
                prev_data = data
                data = enc.read(int(BUFFER_SIZE / 2))

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
