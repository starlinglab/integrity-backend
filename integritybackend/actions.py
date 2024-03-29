from .asset_helper import AssetHelper
from .claim import Claim
from .c2patool import C2patool
from .file_util import FileUtil
from .filecoin import Filecoin
from .iscn import Iscn
from .log_helper import LogHelper
from .numbers import Numbers
from . import config, zip_util, crypto_util

from datetime import datetime, timezone
import json
import os
import shutil
import time
from zipfile import ZipFile
from typing import Tuple, Optional

import requests


_claim = Claim()
_c2patool = C2patool()
_filecoin = Filecoin()
_logger = LogHelper.getLogger()
_file_util = FileUtil()


# pylint: disable=logging-fstring-interpolation
class Actions:
    """Actions for processing assets.

    All actions operate on a ZIP file containing three files:

    1. sha256(asset).ext: the asset file with `ext` matching one of the collection's `asset_extensions`
    2. sha256(asset)-meta-content.json: the metadata associated with the asset file
    3. sha256(asset)-meta-recorder.json: the metadata associated with the recorder of the asset
    """

    def __init__(self) -> None:
        self.zip_dir = None
        self.tmp_dir = None

    @staticmethod
    def _verify_zip(zip_path: str, asset_exts: list[str]) -> Tuple[str, str]:
        """
        Verify the provided ZIP is in the expected preprocessor format.
        The content filename and content SHA-256 hash are returned for further usage.
        An Exception is raised with information if the ZIP is not valid.
        """

        # Verify ZIP name
        input_zip_sha = os.path.splitext(os.path.basename(zip_path))[0]
        if input_zip_sha != _file_util.digest_sha256(zip_path):
            raise Exception(f"SHA-256 of ZIP does not match file name: {zip_path}")

        # Verify ZIP contents are valid and expected
        zip_listing = zip_util.listing(zip_path)
        if len(zip_listing) != 3:
            # ZIP must contain three files: content, meta-content , meta-recorder
            raise Exception(
                f"ZIP at {zip_path} has more than three files: {zip_listing}"
            )
        content_filename = next((s for s in zip_listing if "-meta-" not in s), None)
        if content_filename is None:
            raise Exception(f"ZIP at {zip_path} has no content file: {zip_listing}")
        if "/" in content_filename:
            raise Exception(f"Content file is not at ZIP root: {content_filename}")
        if (
            "*" not in asset_exts
            and os.path.splitext(content_filename)[1][1:] not in asset_exts
        ):
            raise Exception(
                f"Content file in ZIP has wrong extension: {content_filename}"
            )
        content_sha_unverified = os.path.splitext(content_filename)[0]
        if f"{content_sha_unverified}-meta-content.json" not in zip_listing:
            raise Exception(
                f"ZIP at {zip_path} has no content metadata file: {zip_listing}"
            )
        if f"{content_sha_unverified}-meta-recorder.json" not in zip_listing:
            raise Exception(
                f"ZIP at {zip_path} has no recorder metadata file: {zip_listing}"
            )

        # Verify content SHA from name
        content_sha = zip_util.hash_file(zip_path, content_filename)
        if content_sha != content_sha_unverified:
            raise Exception(f"SHA-256 of content does not match file name: {zip_path}")

        _logger.info(f"Content verified for archival: {zip_path}")
        return content_filename, content_sha

    @staticmethod
    def _write_hash_list(
        path,
        input_zip_sha,
        content_sha,
        content_md5,
        content_cid,
        zip_sha,
        zip_md5,
        zip_cid,
        enc_zip_sha,
        enc_zip_md5,
        enc_zip_cid,
        source_id: Optional[str],
        reg_records: Optional[dict] = None,
    ):
        hash_list = {
            "inputBundle": {
                "sha256": input_zip_sha,
            },
            "content": {
                "sha256": content_sha,
                "md5": content_md5,
                "cid": content_cid,
            },
            "archive": {
                "sha256": zip_sha,
                "md5": zip_md5,
                "cid": zip_cid,
            },
            "archiveEncrypted": {
                "sha256": enc_zip_sha,
                "md5": enc_zip_md5,
                "cid": enc_zip_cid,
            },
            "registrationRecords": {},
        }
        if reg_records is not None:
            for k, v in reg_records.items():
                if v is not None:
                    hash_list["registrationRecords"][k] = v
        if source_id is not None:
            hash_list["sourceId"] = source_id

        with open(path, "w") as f:
            f.write(json.dumps(hash_list))
            f.write("\n")

    def archive(self, zip_path: str, org_id: str, collection_id: str):
        """Archive asset.

        Args:
            zip_path: path to asset zip (will be copied, not altered)
            org_id: ID for this organization
            collection_id: string with the unique collection identifier this
                asset is in

        Exceptions are not raised, only logged.
        """

        try:
            self._archive(zip_path, org_id, collection_id)
        finally:
            if self.zip_dir and self.tmp_dir:
                self._purge_from_tmp(self.zip_dir, self.tmp_dir)

    def _archive(self, zip_path: str, org_id: str, collection_id: str):
        action_name = "archive"

        asset_helper = AssetHelper(org_id)

        collection = config.ORGANIZATION_CONFIG.get_collection(org_id, collection_id)
        action = config.ORGANIZATION_CONFIG.get_action(
            org_id, collection_id, action_name
        )
        action_params = action.get("params")
        if action_params["encryption"]["algo"] != "aes-256-cbc":
            raise Exception(
                f"Encryption algo {action_params['encryption']['algo']} not implemented"
            )

        input_zip_sha = os.path.splitext(os.path.basename(zip_path))[0]

        content_filename, content_sha = self._verify_zip(
            zip_path, collection["asset_extensions"]
        )

        # Copy ZIP
        archive_dir = asset_helper.path_for_action(collection_id, action_name)
        tmp_zip = shutil.copy2(zip_path, archive_dir)

        tmp_dir = asset_helper.path_for_action_tmp(collection_id, action_name)
        zip_dir = os.path.join(tmp_dir, content_sha)
        self.tmp_dir = tmp_dir
        self.zip_dir = zip_dir

        # Extract content file
        extracted_content = os.path.join(zip_dir, content_filename)
        _file_util.create_dir(zip_dir)
        zip_util.extract_file(tmp_zip, content_filename, extracted_content)

        # Generate content hashes
        content_cid = _file_util.digest_cidv1(extracted_content)
        content_md5 = _file_util.digest_md5(extracted_content)

        # Extract metadata files
        meta_content_filename = f"{content_sha}-meta-content.json"
        extracted_meta_content = os.path.join(zip_dir, meta_content_filename)
        zip_util.extract_file(tmp_zip, meta_content_filename, extracted_meta_content)
        meta_recorder_filename = f"{content_sha}-meta-recorder.json"
        extracted_meta_recorder = os.path.join(zip_dir, meta_recorder_filename)
        zip_util.extract_file(tmp_zip, meta_recorder_filename, extracted_meta_recorder)

        # Sign with authsign
        if action_params["signers"]["authsign"]["active"]:
            authsign_server_url = action_params["signers"]["authsign"]["server_url"]
            authsign_auth_token = action_params["signers"]["authsign"]["auth_token"]
            _logger.info(f"Content signing by authsign server: {authsign_server_url}")

            def authsign(data, sha, name):
                path = self._authsign_data(
                    tmp_zip, data, sha, authsign_server_url, authsign_auth_token
                )
                if path is None:
                    _logger.error(f"{name} signage failed")
                else:
                    _logger.info(f"{name} signed by authsign server {path}")

            # Sign content hash, content metadata hash, etc
            authsign(extracted_content, content_sha, "content")
            authsign(
                extracted_meta_content,
                _file_util.digest_sha256(extracted_meta_content),
                "content metadata",
            )
            authsign(
                extracted_meta_recorder,
                _file_util.digest_sha256(extracted_meta_recorder),
                "recorder metadata",
            )
        else:
            _logger.info("Content signage with authsign skipped")

        # Register on OpenTimestamps and add that file to zip
        if action_params["registration_policies"]["opentimestamps"]["active"]:
            _logger.info(
                "Secure timestamping of content and metadata with OpenTimestamps"
            )

            def ots(data, name):
                path = self._opentimestamps_data(tmp_zip, data)
                if path is None:
                    _logger.error(f"{name} timestamp registration failed")
                else:
                    _logger.info(
                        f"{name} securely timestamped with OpenTimestamps: {path}"
                    )

            # Content timestamp registration, content metadata timestamp reg., etc.
            ots(extracted_content, "content")
            ots(extracted_meta_content, "content metadata")
            ots(extracted_meta_recorder, "recorder metadata")
        else:
            _logger.info("Timestamp registration with OpenTimestamps skipped")

        # Get archive ZIP hashes
        zip_sha = _file_util.digest_sha256(tmp_zip)
        zip_md5 = _file_util.digest_md5(tmp_zip)
        zip_cid = _file_util.digest_cidv1(tmp_zip)

        # Rename archive zip to SHA-256 of itself
        archive_zip = os.path.join(archive_dir, zip_sha + ".zip")
        os.rename(tmp_zip, archive_zip)
        _logger.info(f"Archive zip generated: {archive_zip}")

        # Encrypt archive ZIP
        aes_key = crypto_util.get_key(action_params["encryption"]["key"])
        tmp_encrypted_zip = os.path.join(archive_dir, zip_sha + ".encrypted")
        _file_util.encrypt(aes_key, archive_zip, tmp_encrypted_zip)

        # Get encrypted ZIP hashes
        enc_zip_sha = _file_util.digest_sha256(tmp_encrypted_zip)
        enc_zip_md5 = _file_util.digest_md5(tmp_encrypted_zip)
        enc_zip_cid = _file_util.digest_cidv1(tmp_encrypted_zip)

        # Rename encrypted ZIP to SHA-256 of itself
        encrypted_zip = os.path.join(archive_dir, enc_zip_sha + ".encrypted")
        os.rename(tmp_encrypted_zip, encrypted_zip)
        _logger.info(f"Encrypted zip generated: {encrypted_zip}")

        with open(extracted_meta_content) as meta_content_f:
            meta_content = json.load(meta_content_f)["contentMetadata"]

        # Register encrypted ZIP on ISCN
        iscn_receipt = None
        if action_params["registration_policies"]["iscn"]["active"]:
            try:
                iscn_receipt = Iscn.register_archive(
                    enc_zip_sha,
                    enc_zip_md5,
                    enc_zip_cid,
                    content_sha,
                    content_md5,
                    content_cid,
                    zip_sha,
                    zip_md5,
                    zip_cid,
                    meta_content["name"],
                    meta_content["description"],
                    meta_content["author"],
                    [org_id, collection_id],
                    meta_content["dateCreated"],
                    json.dumps((meta_content["extras"]), separators=(",", ":")),
                )
            except requests.exceptions.RequestException as e:
                _logger.error(f"Content registration on ISCN failed: {e}")
            else:
                if iscn_receipt is not None:
                    _logger.info(f"Content registered on ISCN: {iscn_receipt}")
                else:
                    _logger.error("Content registration on ISCN failed")
        else:
            _logger.info("Content registration on ISCN skipped")

        # Register encrypted ZIP on Numbers Protocol
        numbers_receipt = None
        if action_params["registration_policies"]["numbersprotocol"]["active"]:
            try:
                chains = action_params["registration_policies"]["numbersprotocol"][
                    "chains"
                ]
                numbers_receipt = Numbers.register_archive(
                    meta_content["name"],
                    meta_content["description"],
                    enc_zip_cid,
                    enc_zip_sha,
                    "application/octet-stream",
                    meta_content["dateCreated"],
                    action_params["registration_policies"]["numbersprotocol"][
                        "custody_token_contract_address"
                    ],
                    meta_content["author"],
                    org_id,
                    collection_id,
                    meta_content["extras"],
                    enc_zip_sha,
                    enc_zip_md5,
                    enc_zip_cid,
                    content_sha,
                    content_md5,
                    content_cid,
                    zip_sha,
                    zip_md5,
                    zip_cid,
                    chains,
                    action_params["registration_policies"]["numbersprotocol"].get(
                        "testnet", False
                    ),
                )
            except requests.exceptions.RequestException as e:
                _logger.error(f"Content registration on Numbers Protocol failed: {e}")
            else:
                for chain in chains:
                    if chain in numbers_receipt:
                        _logger.info(f"Registered on Numbers Protocol chain {chain}")
                    else:
                        # Don't fail for missing registrations, just log
                        _logger.error(
                            f"Registration on Numbers protocol chain {chain} failed"
                        )
        else:
            _logger.info("Content registration on Numbers Protocol skipped")

        # Generate file that contains all the hashes
        action_output_dir = asset_helper.path_for_action_output(
            collection_id, action_name
        )
        hash_list_path = os.path.join(action_output_dir, f"{input_zip_sha}.json")
        self._write_hash_list(
            hash_list_path,
            input_zip_sha,
            content_sha,
            content_md5,
            content_cid,
            zip_sha,
            zip_md5,
            zip_cid,
            enc_zip_sha,
            enc_zip_md5,
            enc_zip_cid,
            # "sourceId" is a reference field to the original content
            # Filename, item number/timestamp, public key, whatever works
            # https://github.com/starlinglab/integrity-backend/issues/116
            meta_content.get("sourceId"),
            {"iscn": iscn_receipt, "numbersProtocol": numbers_receipt},
        )

    def c2pa_proofmode(self, zip_path: str, org_config: dict, collection_id: str):
        """Process a proofmode zip that bundles multiple JPEG assets with metadata,
        and injects C2PA claims to outputted JPEG assets.

        Args:
            zip_path: path to asset zip (will be copied, not altered)
            org_config: configuration dictionary for this organization
            collection_id: string with the unique collection identifier this
                asset is in

        Raises:
            Exception if errors are encountered during processing
        """
        try:
            #Acceptable extensions for proofmode
            # TODO: use starling capture method instead
            C2PA_EXT=[".jpg",".jpeg","m4a"]

            # TODO: change function to take just org_id as param
            action_name = "c2pa-proofmode"
            org_id = org_config["id"]
            asset_helper = AssetHelper(org_id)

            action = config.ORGANIZATION_CONFIG.get_action(
                org_id, collection_id, action_name
            )
            action_params = action.get("params")

            # Get paths
            action_dir = asset_helper.path_for_action(collection_id, action_name)
            action_output_dir = asset_helper.path_for_action_output(
                collection_id, action_name
            )
            action_tmp_dir = asset_helper.path_for_action_tmp(
                collection_id, action_name
            )

            # Verify and copy zip
            input_zip_sha = os.path.splitext(os.path.basename(zip_path))[0]
            if input_zip_sha != _file_util.digest_sha256(zip_path):
                raise Exception(f"SHA-256 of ZIP does not match file name: {zip_path}")
            tmp_zip = shutil.copy2(zip_path, action_tmp_dir)
            bundle_name = f"{input_zip_sha}-images"

            # Define paths for images extracted from proofmode zip
            tmp_img_dir = os.path.join(action_tmp_dir, bundle_name)
            action_img_dir = os.path.join(action_dir, bundle_name)

            meta_content = None
            photographer_id = None
            with ZipFile(tmp_zip) as zipf:
                meta_content_path = next(
                    (s for s in zipf.namelist() if s.endswith("-meta-content.json")),
                    None,
                )
                if meta_content_path is None:
                    raise Exception(f"ZIP at {zip_path} has no content metadata file")
                with zipf.open(meta_content_path) as meta_content_f:
                    meta_content = json.load(meta_content_f)["contentMetadata"]
                    source_name = meta_content.get("author", {}).get("name")
                    if source_name is None:
                        photographer_id = "default"
                    else:
                        photographer_id = asset_helper.filename_safe(source_name)

                # Open content ZIP and extract all JPEGs
                content_zip = next(
                    (s for s in zipf.namelist() if s.endswith(".zip")), None
                )
                if content_zip is None:
                    raise Exception(f"ZIP at {zip_path} has no content file")
                _file_util.create_dir(tmp_img_dir)
                with ZipFile(zipf.open(content_zip)) as content_zip_f:
                    for file_path in content_zip_f.namelist():
                        if os.path.splitext(file_path)[1].lower() in C2PA_EXT:
                            content_zip_f.extract(file_path, tmp_img_dir)

            # Get list of JPEGs
            image_filenames = []
            for filename in os.listdir(tmp_img_dir):
                if os.path.splitext(filename)[1].lower() in C2PA_EXT:
                    image_filenames.append(filename)

            # C2PA-inject all JPEGs
            for filename in image_filenames:
                claim = _claim.generate_c2pa_proofmode(meta_content, filename)
                path = os.path.join(tmp_img_dir, filename)
                _c2patool.run_claim_inject(
                    claim,
                    path,
                    path,
                    action_params["c2pa_cert"],
                    action_params["c2pa_key"],
                    action_params["c2pa_algo"],
                )

            # Process C2PA-injected JPEGs
            for filename in image_filenames:
                # TODO: Why is this needed. fix for m4a as well
                # Rename each image file to .jpg
                path = os.path.join(tmp_img_dir, filename)
                image_path = FileUtil.change_filename_extension(path, ".jpg")
                os.rename(path, image_path)

                # Read claims (requires .jpg extension as input)
                claim_path = FileUtil.change_filename_extension(image_path, ".json")
                _c2patool.run_claim_dump(image_path, claim_path)

            # Copy all C2PA-injected JPEGs to action_dir
            shutil.copytree(tmp_img_dir, action_img_dir, dirs_exist_ok=True)

            # Atomically move all C2PA-injected JPEGs to output folder under photographer ID and date
            shared_dir = os.path.join(
                action_output_dir,
                photographer_id,
                datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                bundle_name,
            )
            if os.path.exists(shared_dir):
                shared_dir = f"{shared_dir}-{int(time.time())}"
            os.renames(tmp_img_dir, shared_dir)
        except Exception as e:
            _logger.error(
                f"{action_name} failed during processing of input file: {zip_path}"
            )
            _logger.error(str(e))
        finally:
            self._purge_from_tmp(tmp_img_dir, action_tmp_dir)
            self._purge_from_tmp(tmp_zip, action_tmp_dir)

    def copy_proofmode(self, zip_path: str, org_config: dict, collection_id: str):
        """Process a proofmode zip that bundles multiple assets with metadata,
        and extracts them to the output folder.

        Args:
            zip_path: path to asset zip (will be copied, not altered)
            org_config: configuration dictionary for this organization
            collection_id: string with the unique collection identifier this
                asset is in

        Raises:
            Exception if errors are encountered during processing
        """
        try:
            # TODO: change function to take just org_id as param
            action_name = "copy-proofmode"
            org_id = org_config["id"]
            asset_helper = AssetHelper(org_id)

            # Get paths
            action_dir = asset_helper.path_for_action(collection_id, action_name)
            action_output_dir = asset_helper.path_for_action_output(
                collection_id, action_name
            )
            action_tmp_dir = asset_helper.path_for_action_tmp(
                collection_id, action_name
            )

            # Verify and copy zip
            input_zip_sha = os.path.splitext(os.path.basename(zip_path))[0]
            if input_zip_sha != _file_util.digest_sha256(zip_path):
                raise Exception(f"SHA-256 of ZIP does not match file name: {zip_path}")
            tmp_zip = shutil.copy2(zip_path, action_tmp_dir)
            bundle_name = f"{input_zip_sha}-images"

            # Define paths for files extracted from proofmode zip
            tmp_img_dir = os.path.join(action_tmp_dir, bundle_name)
            # TODO rename variables, these are not images
            action_img_dir = os.path.join(action_dir, bundle_name)

            meta_content = None
            photographer_id = None
            with ZipFile(tmp_zip) as zipf:
                meta_content_path = next(
                    (s for s in zipf.namelist() if s.endswith("-meta-content.json")),
                    None,
                )
                if meta_content_path is None:
                    raise Exception(f"ZIP at {zip_path} has no content metadata file")
                with zipf.open(meta_content_path) as meta_content_f:
                    meta_content = json.load(meta_content_f)["contentMetadata"]
                    source_name = meta_content.get("author", {}).get("name")
                    if source_name is None:
                        photographer_id = "default"
                    else:
                        photographer_id = asset_helper.filename_safe(source_name)

                # Open content ZIP and extract all files
                content_zip = next(
                    (s for s in zipf.namelist() if s.endswith(".zip")), None
                )
                if content_zip is None:
                    raise Exception(f"ZIP at {zip_path} has no content file")
                _file_util.create_dir(tmp_img_dir)
                with ZipFile(zipf.open(content_zip)) as content_zip_f:
                    for file_path in content_zip_f.namelist():
                        content_zip_f.extract(file_path, tmp_img_dir)

            # Copy all files to action_dir
            shutil.copytree(tmp_img_dir, action_img_dir, dirs_exist_ok=True)

            # Atomically move all files to output folder under photographer ID and date
            shared_dir = os.path.join(
                action_output_dir,
                photographer_id,
                datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                bundle_name,
            )
            if os.path.exists(shared_dir):
                shared_dir = f"{shared_dir}-{int(time.time())}"
            os.renames(tmp_img_dir, shared_dir)
        except Exception as e:
            _logger.error(
                f"{action_name} failed during processing of input file: {zip_path}"
            )
            _logger.error(str(e))
        finally:
            self._purge_from_tmp(tmp_img_dir, action_tmp_dir)
            self._purge_from_tmp(tmp_zip, action_tmp_dir)

    def c2pa_starling_capture(
        self, zip_path: str, org_config: dict, collection_id: str
    ):
        """
        Inject a JPEG from Starling Capture with C2PA information.

        A new asset file is generated in the create-output folder with an original creation claim.

        Args:
            zip_path: path to asset zip (will be copied, not altered)
            org_config: configuration dictionary for this organization
            collection_id: string with the unique collection identifier this asset is in

        Returns:
            the local path to the asset file in the internal directory

        Raises:
            Exception if errors are encountered during processing
        """

        # Setup context

        action_name = "c2pa-starling-capture"
        org_id = org_config["id"]

        asset_helper = AssetHelper(org_id)

        collection = config.ORGANIZATION_CONFIG.get_collection(org_id, collection_id)
        action = config.ORGANIZATION_CONFIG.get_action(
            org_id, collection_id, action_name
        )
        action_params = action.get("params")

        content_filename, content_sha = self._verify_zip(
            zip_path, collection["asset_extensions"]
        )
        content_ext=os.path.splitext(content_filename)[1].lower()

        # Extract content file
        tmp_dir = asset_helper.path_for_action_tmp(collection_id, action_name)
        zip_dir = os.path.join(tmp_dir, content_sha)
        extracted_content = os.path.join(zip_dir, content_filename)
        _file_util.create_dir(zip_dir)
        zip_util.extract_file(zip_path, content_filename, extracted_content)

        # Load meta content
        meta_content_filename = f"{content_sha}-meta-content.json"
        meta_content = zip_util.json_load(zip_path, meta_content_filename)

        # Create temporary files to work with.
        tmp_asset_file = asset_helper.get_tmp_file_fullpath(f".{content_ext}")
        tmp_claim_file = asset_helper.get_tmp_file_fullpath(".json")

        # Inject create claim and read back from file.
        claim = _claim.generate_c2pa_starling_capture(meta_content["contentMetadata"])
        shutil.copy2(extracted_content, tmp_asset_file)
        _c2patool.run_claim_inject(
            claim,
            tmp_asset_file,
            tmp_asset_file,
            action_params["c2pa_cert"],
            action_params["c2pa_key"],
            action_params["c2pa_algo"],
        )
        _c2patool.run_claim_dump(tmp_asset_file, tmp_claim_file)
        
        # Copy the C2PA-injected asset to both the internal and shared asset directories.
        asset_file_hash = _file_util.digest_sha256(tmp_asset_file)

        os.makedirs(os.path.join(asset_helper.path_for_action(collection_id, action_name),"assets"),exist_ok=True)
        internal_asset_file = os.path.join(
            asset_helper.path_for_action(collection_id, action_name),
            "assets",
            asset_file_hash + f".{content_ext}",
        )
        shutil.move(tmp_asset_file, internal_asset_file)
        target_path=os.path.join(
                 asset_helper.path_for_action_output(collection_id, action_name),
                 meta_content["contentMetadata"]["author"].get("name", "unknown"),
                 datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )
        os.makedirs(target_path,exist_ok=True)
        shutil.copy2(
            internal_asset_file,
            target_path
        )
        _logger.info("New asset file added: %s", internal_asset_file)

        # Treat manifest the same way: both internal and shared dirs
        # https://github.com/starlinglab/integrity-backend/pull/130#discussion_r1195401358
        internal_claim_path = os.path.join(
            asset_helper.path_for_action(collection_id, action_name),
            "claims"
        )
        os.makedirs(internal_claim_path,exist_ok=True)
        internal_claim_file = os.path.join(
            internal_claim_path,
            asset_file_hash + ".json",
        )
        shutil.move(tmp_claim_file, internal_claim_file)
        shutil.copy2(
            internal_claim_file,
            os.path.join(
                asset_helper.path_for_action_output(collection_id, action_name),
                meta_content["contentMetadata"]["author"].get("name", "unknown"),
                datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            ),
        )
        _logger.info(
            "New claim file added: %s",
            internal_claim_file,
        )

        return internal_asset_file

    def _authsign_data(
        self, proof_zip_path, extracted_content_path, data_hash, server_url, auth_token
    ):
        proof_file_path = f"{extracted_content_path}.authsign"
        try:
            _file_util.authsign_sign(data_hash, server_url, auth_token, proof_file_path)
            zip_util.append(
                proof_zip_path,
                proof_file_path,
                "proofs/" + os.path.basename(proof_file_path),
            )
        except Exception as e:
            _logger.error(str(e))
        return proof_file_path

    def _opentimestamps_data(self, proof_zip_path, extracted_content_path):
        proof_file_path = f"{extracted_content_path}.ots"
        try:
            _file_util.register_timestamp(extracted_content_path, proof_file_path)
            zip_util.append(
                proof_zip_path,
                proof_file_path,
                "proofs/" + os.path.basename(proof_file_path),
            )
        except Exception as e:
            _logger.error(str(e))
        return proof_file_path

    def _purge_from_tmp(self, purge_target, tmp_root):
        purge_target = purge_target.strip()
        if purge_target and purge_target != "/" and purge_target.startswith(tmp_root):
            # Clean up temporary files
            if os.path.isfile(purge_target):
                os.remove(purge_target)
                _logger.info(f"Purged temporary file at: {purge_target}")
            elif os.path.isdir(purge_target):
                shutil.rmtree(purge_target)
                _logger.info(f"Purged temporary directory at: {purge_target}")
