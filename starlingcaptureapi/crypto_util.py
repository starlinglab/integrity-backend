import logging
import os
from Crypto.Cipher import AES

_logger = logging.getLogger(__name__)


def new_aes_key():
    """Generates a new key for AES-256.

    Returns:
        the key as bytes
    """

    return os.urandom(32)


class AESCipher:
    """
    Handles AES-256-CBC encryption with padding.

    Can only be used for one file/msg, for either encryption or decryption.
    A new file/msg will need a new instance.

    All inputs and outputs are bytes, not strings.
    """

    def __init__(self, key):
        self.key = key
        self.iv = os.urandom(AES.block_size)
        self.cipher = AES.new(self.key, AES.MODE_CBC, self.iv)

    def encrypt(self, raw):
        return self.cipher.encrypt(raw)

    def encrypt_last_block(self, raw):
        return self.cipher.encrypt(self._pad(raw))

    def decrypt(self, enc):
        return self.cipher.decrypt(enc)

    def decrypt_last_block(self, enc):
        return self._unpad(self.cipher.decrypt(enc))

    # Adapted from: https://stackoverflow.com/a/21928790

    @staticmethod
    def _pad(s):
        """PKCS7 padding"""
        return (
            s
            + (AES.block_size - len(s) % AES.block_size)
            * chr(AES.block_size - len(s) % AES.block_size).encode()
        )

    @staticmethod
    def _unpad(s):
        """PKCS7 padding"""
        return s[: -ord(s[len(s) - 1 :])]
