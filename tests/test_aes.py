from crypt import crypt
from .context import file_util
from .context import crypto_util

import os

fu = file_util.FileUtil()

# https://docs.pytest.org/en/latest/how-to/tmp_path.html


def test_encrypt_decrypt(tmp_path):
    # Cleartext is just random bytes
    cleartext = os.urandom(511)  # Not a multiple of 16, tests padding
    print("Cleartext length:", len(cleartext))
    key = crypto_util.new_aes_key()

    clear = tmp_path / "clear.bin"
    clear.write_bytes(cleartext)
    assert clear.read_bytes() == cleartext

    # Write encrypted file
    enc = tmp_path / "enc.bin"
    fu.encrypt(key, str(clear), str(enc))

    # Decrypt file and match cleartext
    dec = tmp_path / "dec.bin"
    fu.decrypt(key, str(enc), str(dec))

    assert dec.read_bytes() == cleartext
