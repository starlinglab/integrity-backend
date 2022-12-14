from . import config
from .crypto_util import AESCipher
from .log_helper import LogHelper

from Crypto.Cipher import AES
from hashlib import sha256, md5
from datetime import datetime, timezone
from pathlib import Path

import errno
import json
import os
import requests
import subprocess
import uuid

_logger = LogHelper.getLogger()


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
    def change_filename_extension(filename, ext: str) -> str:
        """Changes the file extension for the given filename.

        Args:
            filename: the filename to process
            ext: the new file extension

        Returns:
            the filename with the new extension
        """
        return str(Path(filename).with_suffix(ext))

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

    def authsign_sign(
        self,
        data_hash,
        authsign_server_url,
        authsign_auth_token,
        authsign_file_path=None,
    ):
        """
        Sign the provided hash with authsign.
        Args:
            data_hash: hash of data as a hexadecimal string
            authsign_server_url: URL to authsign server
            authsign_auth_token: authorization token to authsign server
            authsign_file_path: optional output path for authsign proof file (.authsign)
        Raises:
            Any errors with the request
        Returns:
            The signature proof as a string
        """

        dt = datetime.now()
        if isinstance(dt, datetime):
            # Convert to ISO format string
            dt = (
                dt.astimezone(timezone.utc)
                .replace(tzinfo=None)
                .isoformat(timespec="seconds")
                + "Z"
            )

        headers = {}
        if authsign_auth_token != "":
            headers = {"Authorization": f"bearer {authsign_auth_token}"}

        r = requests.post(
            authsign_server_url + "/sign",
            headers=headers,
            json={"hash": data_hash, "created": dt},
        )
        r.raise_for_status()
        authsign_proof = r.json()

        # Write proof to file
        if authsign_file_path != None:
            with open(authsign_file_path, "w") as f:
                f.write(json.dumps(authsign_proof))
                f.write("\n")

        return authsign_proof

    def authsign_verify(self, resp, authsign_server_url):
        """
        Verify the provided signed JSON with authsign.
        Args:
            resp: Python object or JSON string
            authsign_server_url: URL to authsign server
        Raises:
            Any unexpected server responses
        Returns:
            bool indicating whether the verification was successful or not
        """

        if not isinstance(resp, str):
            resp = json.dumps(resp)

        r = requests.post(authsign_server_url + "/verify", data=resp)
        if r.status_code == 200:
            return True
        if r.status_code == 400:
            return False

        # Unexpected status code
        r.raise_for_status()

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
    def digest_cidv1(file_path):
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
