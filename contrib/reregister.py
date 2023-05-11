import sys
import os
import shutil
from zipfile import ZipFile
import json
import time

# Disable org config loading
os.environ["RUN_ENV"] = "test"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# pylint: disable=import-error,wrong-import-position
from integritybackend import iscn
from integritybackend import numbers

HELP = """
reregister.py

This script re-registers assets that are missing registrations.

It will search assets in a given directory missing the given registration type,
and prompt you to register them.

Commands:
    fixIscn
    fixAvalanche
    fixNumbers
    fixOpentimestamps

Example usage:

$ pipenv run python3 contrib/reregister.py fixIscn org_id collection_id /path/to/zips /path/to/receipts"""

# Seconds
ISCN_DELAY = 2
NUMBERS_DELAY = 5  # Have to wait for previous block to be made


def assets(path: str):
    # Yield asset Zipfile objects

    for file in os.listdir(path):
        if not file.endswith(".zip"):
            continue

        # Open file without context manager so it can be used elsewhere
        # Python will close the file once it is garbage-collected
        zipf = ZipFile(os.path.join(path, file), "a")
        for zipped_file in zipf.namelist():
            if zipped_file.endswith("-meta-content.json"):
                # Valid asset file
                yield zipf
                break  # Move to next .zip, not next file in this zip


def meta_content_from_asset(zipf: ZipFile) -> dict:
    for zipped_file in zipf.namelist():
        if zipped_file.endswith("-meta-content.json"):
            with zipf.open(zipped_file, "r") as f:
                return json.load(f)["contentMetadata"]

    raise Exception(
        f"No meta-content.json file found in {os.path.basename(zipf.filename)}"
    )


def sha_from_asset(zipf: ZipFile) -> str:
    return os.path.basename(zipf.filename)[:64]


# Maps asset hashes to receipt absolute paths
asset_to_receipt_cache = {}


def receipt_path_from_asset(zipf: ZipFile, receipt_dir: str) -> str:
    # Find the receipt file where archive.sha256 matches the asset name/hash

    sha = sha_from_asset(zipf)
    if sha in asset_to_receipt_cache:
        return asset_to_receipt_cache[sha]

    for receipt in os.listdir(receipt_dir):
        if not (receipt.endswith(".json") and len(receipt) == 69):
            continue

        # Make absolute
        receipt = os.path.join(receipt_dir, receipt)

        # XXX: will be opening receipt files that are already stored in asset_to_receipt_cache
        with open(receipt, "r") as f:
            rjson = json.load(f)

        if rjson["archive"]["sha256"] in asset_to_receipt_cache:
            # Already stored and doesn't match our asset
            continue

        # New receipt file, store and check
        asset_to_receipt_cache[rjson["archive"]["sha256"]] = receipt
        if sha in asset_to_receipt_cache:
            return asset_to_receipt_cache[sha]

    raise Exception(f"Couldn't find matching receipt file for asset: {sha}")


def receipt_has_iscn(receipt: dict) -> bool:
    return (
        len(receipt["registrationRecords"].get("iscn", {})) == 2
        and receipt["registrationRecords"]["iscn"].get("txHash")
        and receipt["registrationRecords"]["iscn"].get("iscnId")
    )


def receipt_has_avalanche(receipt: dict) -> bool:
    return bool(
        receipt["registrationRecords"].get("numbersProtocol", {}).get("avalancheTxHash")
    )


def receipt_has_numbers(receipt: dict) -> bool:
    return bool(
        receipt["registrationRecords"].get("numbersProtocol", {}).get("numbersTxHash")
    )


def replace_receipt(zipf: ZipFile, receipt_dir: str, receipt: dict):
    receipt_path = receipt_path_from_asset(zipf, receipt_dir)
    if not os.path.exists(receipt_path + ".orig"):
        # Only make backup if older backup does not already exist
        shutil.copy2(receipt_path, receipt_path + ".orig")
    with open(receipt_path, "w") as f:
        json.dump(receipt, f)


def register_iscn(
    receipt: dict, content_metadata: dict, org_id: str, collection_id: str
):
    """
    Registers ISCN and returns reciept or None if failed.
    """

    return iscn.Iscn.register_archive(
        receipt["archiveEncrypted"]["sha256"],
        receipt["archiveEncrypted"]["md5"],
        receipt["archiveEncrypted"]["cid"],
        receipt["content"]["sha256"],
        receipt["content"]["md5"],
        receipt["content"]["cid"],
        receipt["archive"]["sha256"],
        receipt["archive"]["md5"],
        receipt["archive"]["cid"],
        content_metadata["name"],
        content_metadata["description"],
        content_metadata["author"],
        [org_id, collection_id],
        content_metadata["dateCreated"],
        json.dumps((content_metadata["extras"]), separators=(",", ":")),
    )


def register_numbers(
    receipt: dict,
    content_metadata: dict,
    org_id: str,
    collection_id: str,
    custody_token_contract_addr: str = "",
):
    return numbers.Numbers.register_archive(
        content_metadata["name"],
        content_metadata["description"],
        receipt["archiveEncrypted"]["cid"],
        receipt["archiveEncrypted"]["sha256"],
        "application/octet-stream",
        content_metadata["dateCreated"],
        custody_token_contract_addr,
        content_metadata["author"],
        org_id,
        collection_id,
        content_metadata["extras"],
        receipt["archiveEncrypted"]["sha256"],
        receipt["archiveEncrypted"]["md5"],
        receipt["archiveEncrypted"]["cid"],
        receipt["content"]["sha256"],
        receipt["content"]["md5"],
        receipt["content"]["cid"],
        receipt["archive"]["sha256"],
        receipt["archive"]["md5"],
        receipt["archive"]["cid"],
    )


def register_avalanche(
    receipt: dict,
    content_metadata: dict,
    org_id: str,
    collection_id: str,
    custody_token_contract_addr: str = "",
):
    """
    Just calls register_numbers for now, as re-registering Numbers is what registers us on Avalanche also.
    """
    return register_numbers(
        receipt, content_metadata, org_id, collection_id, custody_token_contract_addr
    )


def fix_process(
    valid_func,  # Like receipt_has_iscn
    register_func,  # Like register_iscn
    reg_name: str,
    json_name: str,
    delay: int,
    asset_dir: str,
    receipt_dir: str,
    org_id: str,
    collection_id: str,
    confirmation_msg: str = "Do you want to register them now? (y/N) ",
):
    """
    Generic function to find broken assets and fix them if the user wants.
    """

    total_assets_n = 0
    broken_assets_n = 0
    broken_assets = []
    broken_receipts = []

    print()

    for asset in assets(asset_dir):
        total_assets_n += 1
        with open(receipt_path_from_asset(asset, receipt_dir), "r") as f:
            receipt = json.load(f)
        if not valid_func(receipt):
            broken_assets_n += 1
            broken_assets.append(asset)
            broken_receipts.append(receipt)
            print(os.path.basename(asset.filename))

    if broken_assets_n == 0:
        print(
            f"{total_assets_n} found. No assets are missing {reg_name} registrations."
        )
        sys.exit(0)

    # There are broken assets
    print(
        f"\n{broken_assets_n} out of {total_assets_n} are missing {reg_name} registrations, see list above."
    )
    if input(confirmation_msg) != "y":
        sys.exit(0)

    # Said yes
    i = 1
    for asset, receipt in zip(broken_assets, broken_receipts):
        content_metadata = meta_content_from_asset(asset)
        new_receipt = register_func(receipt, content_metadata, org_id, collection_id)
        if new_receipt is None:
            print(
                f"{reg_name} registration failed, stopping: {os.path.basename(asset.filename)}"
            )
            sys.exit(1)

        receipt["registrationRecords"][json_name] = new_receipt
        replace_receipt(asset, receipt_dir, receipt)
        print(f"Registered {i} of {broken_assets_n}")

        i += 1

        # Throttling
        time.sleep(delay)


def main():
    if len(sys.argv) != 6:
        print("Must provide command and paths.")
        print(HELP)
        sys.exit(1)

    cmd = sys.argv[1]
    org_id = sys.argv[2]
    collection_id = sys.argv[3]
    asset_dir = sys.argv[4]
    receipt_dir = sys.argv[5]

    if cmd not in ["fixIscn", "fixAvalanche", "fixNumbers", "fixOpentimestamps"]:
        print("Invalid command.")
        print(HELP)
        sys.exit(1)

    if cmd == "fixOpentimestamps":
        print("Not implemented.")
        sys.exit(0)

    if cmd == "fixIscn":
        if "ISCN_SERVER" not in os.environ:
            print("ISCN_SERVER env var not defined, aborting.")
            sys.exit(1)

        fix_process(
            receipt_has_iscn,
            register_iscn,
            "ISCN",
            "iscn",
            ISCN_DELAY,
            asset_dir,
            receipt_dir,
            org_id,
            collection_id,
        )
    elif cmd == "fixAvalanche":
        # Avalanche is done by numbers so values are similar

        addr = input("Provide custody token contract address if available: ").strip()
        fix_process(
            receipt_has_avalanche,
            lambda *args: register_avalanche(*args, custody_token_contract_addr=addr),
            "Avalanche",
            "numbersProtocol",
            NUMBERS_DELAY,
            asset_dir,
            receipt_dir,
            org_id,
            collection_id,
            confirmation_msg="Do you want to register them now? This will also re-register on Numbers. (y/N) ",
        )

    elif cmd == "fixNumbers":
        addr = input("Provide custody token contract address if available: ").strip()
        fix_process(
            receipt_has_numbers,
            lambda *args: register_numbers(*args, custody_token_contract_addr=addr),
            "Numbers",
            "numbersProtocol",
            NUMBERS_DELAY,
            asset_dir,
            receipt_dir,
            org_id,
            collection_id,
            confirmation_msg="Do you want to register them now? This will also re-register on Avalanche. (y/N) ",
        )


if __name__ == "__main__":
    main()
