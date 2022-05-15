from .asset_helper import AssetHelper
from .claim import Claim
from .claim_tool import ClaimTool
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


_claim = Claim()
_claim_tool = ClaimTool()
_filecoin = Filecoin()
_logger = LogHelper.getLogger()
_file_util = FileUtil()


class Actions:
    """Actions for processing assets.

    All actions operate on a ZIP file containing three files:

    1. sha256(asset).ext: the asset file with `ext` matching one of the collection's `asset_extensions`
    2. sha256(asset)-meta-content.json: the metadata associated with the asset file
    3. sha256(asset)-meta-recorder.json: the metadata associated with the recorder of the asset
    """

    def archive(self, zip_path: str, org_config: dict, collection_id: str):
        """Archive asset.

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
            action_name = "archive"
            org_id = org_config["id"]

            asset_helper = AssetHelper(org_id)
            _file_util = FileUtil()

            collection = config.ORGANIZATION_CONFIG.get_collection(
                org_id, collection_id
            )
            action = config.ORGANIZATION_CONFIG.get_action(
                org_id, collection_id, action_name
            )
            action_params = action.get("params")
            if action_params["encryption"]["algo"] != "aes-256-cbc":
                raise Exception(
                    f"Encryption algo {action_params['encryption']['algo']} not implemented"
                )

            # Verify ZIP name
            input_zip_sha = os.path.splitext(os.path.basename(zip_path))[0]
            if input_zip_sha != _file_util.digest_sha256(zip_path):
                raise Exception(f"SHA-256 of ZIP does not match file name: {zip_path}")

            # Copy ZIP
            archive_dir = asset_helper.path_for_action(collection_id, action_name)
            tmp_zip = shutil.copy2(zip_path, archive_dir)

            # Verify ZIP contents are valid and expected
            zip_listing = zip_util.listing(tmp_zip)
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
                "*" not in collection["asset_extensions"]
                and os.path.splitext(content_filename)[1][1:]
                not in collection["asset_extensions"]
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

            # Extract content file
            tmp_dir = asset_helper.path_for_action_tmp(collection_id, action_name)
            zip_dir = os.path.join(tmp_dir, content_sha_unverified)
            extracted_content = os.path.join(zip_dir, content_filename)
            _file_util.create_dir(zip_dir)
            zip_util.extract_file(tmp_zip, content_filename, extracted_content)

            # Generate content hashes and verify
            content_sha = _file_util.digest_sha256(extracted_content)
            if content_sha != content_sha_unverified:
                raise Exception(
                    f"SHA-256 of content does not match file name: {zip_path}"
                )
            content_cid = _file_util.digest_cidv1(extracted_content)
            content_md5 = _file_util.digest_md5(extracted_content)
            _logger.info(f"Content verified for archival: {zip_path}")

            # Extract metadata files
            meta_content_filename = f"{content_sha}-meta-content.json"
            extracted_meta_content = os.path.join(zip_dir, meta_content_filename)
            zip_util.extract_file(
                tmp_zip, meta_content_filename, extracted_meta_content
            )
            meta_recorder_filename = f"{content_sha}-meta-recorder.json"
            extracted_meta_recorder = os.path.join(zip_dir, meta_recorder_filename)
            zip_util.extract_file(
                tmp_zip, meta_recorder_filename, extracted_meta_recorder
            )

            # Sign with authsign
            if action_params["signers"]["authsign"]["active"]:
                authsign_server_url = action_params["signers"]["authsign"]["server_url"]
                authsign_auth_token = action_params["signers"]["authsign"]["auth_token"]
                _logger.info(
                    f"Content signing by authsign server: {authsign_server_url}"
                )

                # Sign content hash
                content_authsign_path = self._authsign_data(
                    tmp_zip,
                    extracted_content,
                    content_sha,
                    authsign_server_url,
                    authsign_auth_token,
                )
                _logger.info(
                    f"Content signed by authsign server: {content_authsign_path}"
                )

                # Sign content metadata hash
                meta_content_sha = _file_util.digest_sha256(extracted_meta_content)
                meta_content_authsign_path = self._authsign_data(
                    tmp_zip,
                    extracted_meta_content,
                    meta_content_sha,
                    authsign_server_url,
                    authsign_auth_token,
                )
                if meta_content_authsign_path != None:
                    _logger.info(
                        f"Metadata of content signed by authsign server: {meta_content_authsign_path}"
                    )
                else:
                    _logger.info(f"Metadata of content signage failed")

                # Sign recorder metadata hash
                meta_recorder_sha = _file_util.digest_sha256(extracted_meta_recorder)
                meta_recorder_authsign_path = self._authsign_data(
                    tmp_zip,
                    extracted_meta_recorder,
                    meta_recorder_sha,
                    authsign_server_url,
                    authsign_auth_token,
                )
                if meta_recorder_authsign_path != None:
                    _logger.info(
                        f"Metadata of recorder signed by authsign server: {meta_recorder_authsign_path}"
                    )
                else:
                    _logger.info(f"Metadata of recorder signage failed")
            else:
                _logger.info(f"Content signage with authsign skipped")

            # Register on OpenTimestamp and add that file to zip
            if action_params["registration_policies"]["opentimestamps"]["active"]:
                content_ots_path = f"{extracted_content}.ots"
                _file_util.register_timestamp(extracted_content, content_ots_path)
                zip_util.append(
                    tmp_zip,
                    content_ots_path,
                    "proofs/" + os.path.basename(content_ots_path),
                )
                _logger.info(
                    f"Content registered on opentimestamps: {content_ots_path}"
                )
            else:
                _logger.info(f"Content registration on opentimestamps skipped")

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

            # Register encrypted ZIP on ISCN
            if action_params["registration_policies"]["opentimestamps"]["active"]:
                with open(extracted_meta_content) as meta_content_f:
                    meta_content = json.load(meta_content_f)
                    iscn_record = {
                        "contentFingerprints": [
                            f"hash://sha256/{enc_zip_sha}",
                            f"hash://md5/{enc_zip_md5}",
                            f"ipfs://{enc_zip_cid}",
                        ],
                        "stakeholders": [
                            {
                                "contributionType": "http://schema.org/citation",
                                "footprint": f"hash://sha256/{content_sha}",
                                "description": "The SHA-256 of the original content.",
                            },
                            {
                                "contributionType": "http://schema.org/citation",
                                "footprint": f"hash://md5/{content_md5}",
                                "description": "The MD5 of the original content.",
                            },
                            {
                                "contributionType": "http://schema.org/citation",
                                "footprint": f"ipfs://{content_cid}",
                                "description": "The CID of the original content.",
                            },
                            {
                                "contributionType": "http://schema.org/citation",
                                "footprint": f"hash://sha256/{zip_sha}",
                                "description": "The SHA-256 of the unencrypted archive.",
                            },
                            {
                                "contributionType": "http://schema.org/citation",
                                "footprint": f"hash://md5/{zip_md5}",
                                "description": "The MD5 of the unencrypted archive.",
                            },
                            {
                                "contributionType": "http://schema.org/citation",
                                "footprint": f"ipfs://{zip_cid}",
                                "description": "The CID of the unencrypted archive.",
                            },
                        ],
                        "type": "Record",
                        "name": meta_content["name"],
                        "description": meta_content["description"],
                        "author": meta_content["author"],
                        "usageInfo": "Encrypted with AES-256 by Starling Lab.",
                        "keywords": [org_id, collection_id],
                        "datePublished": meta_content["dateCreated"],
                        "url": "",
                        "recordNotes": json.dumps(
                            (meta_content["extras"]), separators=(",", ":")
                        ),
                    }
                    iscnId = Iscn.register(iscn_record)
                    if iscnId is not None:
                        _logger.info(f"Content registered on iscn: {iscnId}")
                    else:
                        _logger.error("Content registration on iscn failed")
            else:
                _logger.info("Content registration on iscn skipped")

            # TODO: Register encrypted ZIP on Numbers Protocol

            # Generate file that contains all the hashes
            action_output_dir = asset_helper.path_for_action_output(
                collection_id, action_name
            )
            hash_list_path = os.path.join(action_output_dir, f"{input_zip_sha}.json")
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
            }
            if iscnId is not None:
                hash_list["registrationRecords"] = {"iscnId": iscnId}
            with open(hash_list_path, "w") as f:
                f.write(json.dumps(hash_list))
                f.write("\n")
        except Exception as e:
            _logger.error(
                f"{action_name} failed during processing of input file: {zip_path}"
            )
            _logger.error(str(e))
        finally:
            self._purge_from_tmp(zip_dir, tmp_dir)

    def c2pa_starling_capture(self, asset_fullpath, jwt_payload, meta):
        """Process asset with create action.
        A new asset file is generated in the create-output folder with an original creation claim.

        Args:
            asset_fullpath: the local path to the asset file
            jwt_payload: a JWT payload containing metadata
            meta: dictionary with the 'meta' section of the incoming multipart request

        Returns:
            the local path to the asset file in the internal directory

        Raises:
            Exception if errors are encountered during processing
        """
        asset_helper = AssetHelper.from_jwt(jwt_payload)
        # Create temporary files to work with.
        tmp_asset_file = asset_helper.get_tmp_file_fullpath(".jpg")
        tmp_claim_file = asset_helper.get_tmp_file_fullpath(".json")

        # Inject create claim and read back from file.
        claim = _claim.generate_create(jwt_payload, meta)
        shutil.copy2(asset_fullpath, tmp_asset_file)
        _claim_tool.run_claim_inject(claim, tmp_asset_file, None)
        _claim_tool.run_claim_dump(tmp_asset_file, tmp_claim_file)

        # Copy the C2PA-injected asset to both the internal and shared asset directories.
        internal_asset_file = asset_helper.get_internal_file_fullpath(tmp_asset_file)
        shutil.move(tmp_asset_file, internal_asset_file)
        subfolders = [
            jwt_payload.get("author", {}).get("name"),
            datetime.datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        ]
        shutil.copy2(
            internal_asset_file, asset_helper.get_assets_create_output(subfolders)
        )
        _logger.info("New asset file added: %s", internal_asset_file)
        internal_claim_file = asset_helper.get_internal_claim_fullpath(
            internal_asset_file
        )
        shutil.move(tmp_claim_file, internal_claim_file)
        _logger.info(
            "New claim file added to the internal claims directory: %s",
            internal_claim_file,
        )
        return internal_asset_file

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
            # TODO: change function to take just org_id as param
            action_name = "c2pa-proofmode"
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
                    meta_content = json.load(meta_content_f)
                    photographer_id = asset_helper.filename_safe(
                        meta_content["private"]["signal"]["sourceName"]
                    )

                # Open content ZIP and extract all JPEGs
                content_zip = next(
                    (s for s in zipf.namelist() if s.endswith(".zip")), None
                )
                if content_zip is None:
                    raise Exception(f"ZIP at {zip_path} has no content file")
                _file_util.create_dir(tmp_img_dir)
                with ZipFile(zipf.open(content_zip)) as content_zip_f:
                    for file_path in content_zip_f.namelist():
                        if os.path.splitext(file_path)[1].lower() in [".jpg", ".jpeg"]:
                            content_zip_f.extract(file_path, tmp_img_dir)

            # Get list of JPEGs
            image_filenames = []
            for filename in os.listdir(tmp_img_dir):
                if filename.lower().endswith(".jpg") or filename.lower().endswith(
                    ".jpeg"
                ):
                    image_filenames.append(filename)

            # C2PA-inject all JPEGs
            for filename in image_filenames:
                claim = _claim.generate_c2pa_proofmode(
                    meta_content, filename
                )
                path = os.path.join(tmp_img_dir, filename)
                _claim_tool.run_claim_inject(claim, path, None)

            # Process C2PA-injected JPEGs
            for filename in image_filenames:
                # Rename each image file to .jpg
                path = os.path.join(tmp_img_dir, filename)
                image_path = FileUtil.change_filename_extension(path, ".jpg")
                os.rename(path, image_path)

                # Read claims (requires .jpg extension as input)
                claim_path = FileUtil.change_filename_extension(image_path, ".json")
                _claim_tool.run_claim_dump(image_path, claim_path)

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

    # def c2pa_add(self, asset_fullpath, org_config, collection_id):
    #     """Process asset with add action.
    #     The provided asset file is added to the asset management system and renamed to its internal identifier in the add-output folder.

    #     Args:
    #         asset_fullpath: the local path to the asset file
    #         org_config: configuration dictionary for this organization
    #         collection_id: string with the unique collection identifier this
    #             asset is in

    #     Returns:
    #         the local path to the asset file in the internal directory
    #     """
    #     asset_helper = AssetHelper(org_config.get("id"))
    #     return self._add(
    #         asset_fullpath,
    #         asset_helper.path_for(collection_id, "c2pa-add", output=True),
    #         asset_helper,
    #     )

    # def c2pa_update(self, asset_fullpath, org_config, collection_id):
    #     """Process asset with update action.
    #     A new asset file is generated in the update-output folder with a claim that links it to a parent asset identified by its filename.

    #     Args:
    #         asset_fullpath: the local path to the asset file
    #         org_config: configuration dictionary for this organization
    #         collection_id: string with the unique collection identifier this
    #             asset is in

    #     Returns:
    #         the local path to the asset file in the internal directory
    #     """
    #     organization_id = org_config.get("id")
    #     asset_helper = AssetHelper(organization_id)
    #     return self._update(
    #         asset_fullpath,
    #         _claim.generate_update(org_config, collection_id),
    #         asset_helper.path_for(collection_id, "c2pa-update", output=True),
    #         asset_helper,
    #     )

    # def c2pa_store(self, asset_fullpath, org_config, collection_id):
    #     """Process asset with store action.
    #     The provided asset stored on decentralized storage, then a new asset file is generated in the store-output folder with a storage claim.

    #     Args:
    #         asset_fullpath: the local path to the asset file
    #         org_config: configuration dictionary for this organization
    #         collection_id: string with the unique collection identifier this
    #             asset is in

    #     Returns:
    #         the local path to the asset file in the internal directory
    #     """
    #     # Add uploaded asset to the internal directory.
    #     added_asset = self._add(asset_fullpath, None)

    #     # Store asset to IPFS and Filecoin.
    #     ipfs_cid = _filecoin.upload(added_asset)
    #     _logger.info("Asset file uploaded to IPFS with CID: %s", ipfs_cid)

    #     organization_id = org_config.get("id")
    #     return self._update(
    #         added_asset,
    #         _claim.generate_store(ipfs_cid.organization_id),
    #         AssetHelper(organization_id).path_for(
    #             collection_id, "c2pa-store", output=True
    #         ),
    #     )

    # def c2pa_custom(self, asset_fullpath, org_config, collection_id):
    #     """Process asset with custom action.
    #     A new asset file is generated in the custom-output folder with a claim that links it to a parent asset identified by its filename.

    #     Args:
    #         asset_fullpath: the local path to the asset file
    #         org_config: configuration dictionary for this organization
    #         collection_id: string with the unique collection identifier this
    #             asset is in

    #     Returns:
    #         the local path to the asset file in the internal directory
    #     """
    #     organization_id = org_config.get("id")
    #     asset_helper = AssetHelper(organization_id)

    #     # Add uploaded asset to the internal directory.
    #     added_asset = self._add(asset_fullpath, None)

    #     # Parse file name to get the search key.
    #     file_name, _ = os.path.splitext(os.path.basename(added_asset))

    #     # Find custom assertions for file.
    #     custom_assertions = self._load_custom_assertions().get(file_name)
    #     if custom_assertions is None:
    #         _logger.warning("Could not find custom assertions for asset")
    #     else:
    #         _logger.info("Found custom assertions for asset")
    #     return self._update(
    #         added_asset,
    #         _claim.generate_custom(custom_assertions),
    #         asset_helper.path_for(collection_id, "c2pa-custom", output=True),
    #         asset_helper,
    #     )

    # def _add(self, asset_fullpath, output_dir, asset_helper):
    #     # Create temporary files to work with.
    #     tmp_asset_file = asset_helper.get_tmp_file_fullpath(".jpg")
    #     time.sleep(1)
    #     _logger.info("File size: %s", os.path.getsize(asset_fullpath))
    #     shutil.copy2(asset_fullpath, tmp_asset_file)

    #     # Copy asset to both the internal and shared asset directories.
    #     internal_asset_file = asset_helper.get_internal_file_fullpath(tmp_asset_file)
    #     shutil.move(tmp_asset_file, internal_asset_file)
    #     if output_dir is not None:
    #         shutil.copy2(internal_asset_file, output_dir)
    #     _logger.info("New asset file added: %s", internal_asset_file)

    #     return internal_asset_file

    # def _update(self, asset_fullpath, claim, output_dir, asset_helper):
    #     # Create temporary files to work with.
    #     tmp_asset_file = asset_helper.get_tmp_file_fullpath(".jpg")
    #     tmp_claim_file = asset_helper.get_tmp_file_fullpath(".json")

    #     # Parse file name to get internal name for parent file.
    #     file_name, file_extension = os.path.splitext(os.path.basename(asset_fullpath))
    #     parent_file = os.path.join(
    #         asset_helper.get_assets_internal(), # removed
    #         file_name.partition("_")[0].partition("-")[0] + file_extension,
    #     )

    #     # Inject update claim and read back from file.
    #     time.sleep(1)
    #     _logger.info("File size: %s", os.path.getsize(asset_fullpath))
    #     shutil.copy2(asset_fullpath, tmp_asset_file)
    #     _logger.info("Searching for parent file: %s", parent_file)
    #     if not os.path.isfile(parent_file):
    #         raise Exception(f"Expected {parent_file} to be a file, but it isn't")

    #     _logger.info("_update() action found parent file for asset: %s", parent_file)
    #     _claim_tool.run_claim_inject(claim, tmp_asset_file, parent_file)
    #     _claim_tool.run_claim_dump(tmp_asset_file, tmp_claim_file)
    #     # Copy the C2PA-injected asset to both the internal and shared asset directories.
    #     internal_asset_file = asset_helper.get_internal_file_fullpath(tmp_asset_file)
    #     shutil.move(tmp_asset_file, internal_asset_file)
    #     if output_dir is not None:
    #         shutil.copy2(internal_asset_file, output_dir)
    #     _logger.info("New asset file added: %s", internal_asset_file)
    #     internal_claim_file = asset_helper.get_internal_claim_fullpath(
    #         internal_asset_file
    #     )
    #     shutil.move(tmp_claim_file, internal_claim_file)
    #     _logger.info(
    #         "New claim file added to the internal claims directory: %s",
    #         internal_claim_file,
    #     )
    #     return internal_asset_file

    # def _load_custom_assertions(self):
    #     """Loads custom assertions from file.

    #     Return:
    #         a dictionary with custom assertions mapped to asset name
    #     """
    #     custom_assertions_dictionary = {}
    #     custom_assertions_path = config.CUSTOM_ASSERTIONS_DICTIONARY
    #     try:
    #         with open(custom_assertions_path, "r") as f:
    #             custom_assertions_dictionary = json.load(f)
    #             _logger.info(
    #                 "Successfully loaded custom assertions dictionary: %s",
    #                 custom_assertions_path,
    #             )
    #     except Exception as err:
    #         _logger.info(
    #             "No custom assertions dictionary found: %s",
    #             custom_assertions_path,
    #         )
    #     return custom_assertions_dictionary

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
