from Crypto.Hash import SHA256
from Crypto.PublicKey import ECC
from Crypto.Signature import DSS

from .log_helper import LogHelper
from .file_util import FileUtil

_logger = LogHelper.getLogger()

_file_util = FileUtil()


def verify_create_hashes(asset_path: str, data: dict) -> bool:
    """Verify asset hashes in the data sent to the create action.

    Args:
        asset_path: the local path to the asset file
        data: dictionary with the 'meta' and 'signature' sections of the request

    Returns:
        True if the hashes matched the asset, False if not

    Raises:
        ValueError or KeyError if fields are missing
        Exception if hashes aren't all the same in the JSON
        File I/O errors if there's an issue reading the asset file
    """

    if data.get("meta") is None:
        raise ValueError("meta must be present, but got None")
    if data.get("signature") is None:
        raise ValueError("signature must be present, but got None")

    # First check all hashes match

    meta_hash = data["meta"]["proof"]["hash"]
    sig_hash = data["signature"][0]["proofHash"]

    if meta_hash != sig_hash:
        raise Exception("The meta hash does not equal the first signature hash")

    if len(data["signature"]) > 1:
        # Check all hashes for each signature match
        for sig in data["signatures"][1:]:
            if sig.get("proofHash") != sig_hash:
                raise Exception("Not all proofHash fields of signatures match")

    # Now actually verify the hash
    asset_hash = _file_util.digest_sha256(asset_path)
    return sig_hash == asset_hash


def verify_all(meta_raw: str, signatures: dict) -> bool:
    """Verify all signatures.

    Args:
        meta_raw: string containing JSON meta information, unmodified from POST
                  request
        signatures: 'signature' section of the request data

    Returns:
        True if all signatures verified, False if not

    Raises:
        NotImplementedError if one of the signature providers is not recognized
    """

    for sig in signatures:
        if sig["provider"] == "AndroidOpenSSL":
            if not _verify_androidopenssl(meta_raw, sig):
                return False
        elif sig["provider"] == "Zion":
            if not _verify_zion(meta_raw, sig):
                return False
        else:
            raise NotImplementedError(f"Provider {sig['provider']} not implemented")

    return True


def _verify_androidopenssl(meta_raw: str, signature: dict) -> bool:
    # Adapted from signature verification example
    # https://www.pycryptodome.org/en/latest/src/signature/dsa.html

    key = ECC.import_key(bytes.fromhex(signature["publicKey"]))
    h = SHA256.new(meta_raw.encode())
    verifier = DSS.new(key, "fips-186-3", encoding="der")
    try:
        verifier.verify(h, bytes.fromhex(signature["signature"]))
        return True
    except ValueError:
        return False


def _verify_zion(meta_raw: str, signature: dict) -> bool:
    return False
