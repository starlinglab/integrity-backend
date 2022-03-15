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

    def __init__(self, key, iv=None):
        self.key = key
        self.iv = os.urandom(AES.block_size) if iv is None else iv
        self.cipher = AES.new(self.key, AES.MODE_CBC, self.iv)

    def encrypt(self, raw):
        return self.cipher.encrypt(raw)

    def encrypt_last_block(self, raw):
        return self.cipher.encrypt(self._pad(raw))

    def decrypt(self, enc):
        return self.cipher.decrypt(enc)

    def decrypt_last_block(self, enc):
        return self._unpad(self.cipher.decrypt(enc))

    # Padding funcs adapted from: https://stackoverflow.com/a/21928790
    #
    # PKCS7 padding is pretty standard for AES-CBC, and it's what WebCrypto
    # and therefore the lit-js-sdk uses.

    @staticmethod
    def _pad(b):
        """PKCS7 padding"""
        return (
            b
            + (AES.block_size - len(b) % AES.block_size)
            * chr(AES.block_size - len(b) % AES.block_size).encode()
        )

    @staticmethod
    def _unpad(b):
        """PKCS7 unpadding"""
        if len(b) == 0:
            return b""
        return b[: -ord(b[len(b) - 1 :])]
