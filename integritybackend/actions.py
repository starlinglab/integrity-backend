from .asset_helper import AssetHelper
from .claim import Claim
from .claim_tool import ClaimTool
from .file_util import FileUtil
from .filecoin import Filecoin
from .iscn import Iscn
from . import config, zip_util, crypto_util

import datetime
import json
import logging
import os
import shutil
import time


_claim = Claim()
_claim_tool = ClaimTool()
_filecoin = Filecoin()
_logger = logging.getLogger(__name__)


class Actions:
    """Actions for processing assets.

    All actions operate on:
        * an "asset", represented by its full path on the local filesystem
        * some metadata

    In an ideal future, all actions would be refactored to accept the exact same
    inputs: an asset path and a generalized metadata container or configuration
    object.
    """

    def archive(self, asset_fullpath: str, org_config: dict, collection_id: str):
        """Archive asset.

        Args:
            asset_fullpath: the local path to the asset file
            org_config: configuration dictionary for this organization
            collection_id: string with the unique collection identifier this
                asset is in

        Returns:
            TODO

        Raises:
            Exception if errors are encountered during processing
        """

        zip_path = asset_fullpath
        asset_helper = AssetHelper(org_config["id"])
        file_util = FileUtil()

        org_id = org_config["id"]

        collection_config = config.ORGANIZATION_CONFIG.get_collection(
            org_id, collection_id
        )
        action = config.ORGANIZATION_CONFIG.get_action(
            org_id, collection_id, "archive"
        )

        action_config = action.get('params')

        if action_config["encryption"]["algo"] != "aes-256-cbc":
            raise Exception(
                f"Encryption algo {action_config['encryption']['algo']} not implemented"
            )

        # Verify ZIP name
        input_zip_sha = os.path.splitext(os.path.basename(zip_path))[0]
        if input_zip_sha != file_util.digest_sha256(zip_path):
            raise Exception(
                "SHA-256 of ZIP does not match name: " + os.path.basename(zip_path)
            )

        # Copy ZIP
        archive_dir = asset_helper.get_archive_dir(collection_id)
        tmp_zip = shutil.copy2(zip_path, archive_dir)

        # Verify zip contents are valid and expected
        zip_listing = zip_util.listing(tmp_zip)
        if len(zip_listing) > 3:
            # Should only have three: content, recorder meta, content meta
            raise Exception(
                f"ZIP at {zip_path} has more than three files: {zip_listing}"
            )

        content_filename = next((s for s in zip_listing if "-meta-" not in s), None)
        if content_filename is None:
            raise Exception(f"ZIP at {zip_path} has no content file: {zip_listing}")

        if "/" in content_filename:
            raise Exception(f"Content file is not at ZIP root: {content_filename}")

        if (
            os.path.splitext(content_filename)[1][1:]
            not in collection_config["asset_extensions"]
        ):
            raise Exception(
                f"Content file in ZIP has wrong extension: {content_filename}"
            )

        # Extract content file
        bundle_sha = os.path.splitext(content_filename)[0]
        tmp_dir = asset_helper.get_tmp_collection_dir(collection_id, "archive")
        zip_dir = os.path.join(tmp_dir, bundle_sha)
        extracted_content = os.path.join(zip_dir, content_filename)
        file_util.create_dir(zip_dir)
        zip_util.extract_file(tmp_zip, content_filename, extracted_content)

        # Generate content hashes
        content_sha = file_util.digest_sha256(extracted_content)
        content_cid = file_util.digest_cidv1(extracted_content)
        content_md5 = file_util.digest_md5(extracted_content)

        # Rename to export name: SHA-256 of content file
        final_zip = os.path.join(archive_dir, content_sha + ".zip")
        os.rename(tmp_zip, final_zip)

        # Register on OpenTimestamp and add that file to zip
        content_ots = extracted_content + ".ots"
        file_util.register_timestamp(extracted_content, content_ots)
        zip_util.append(
            final_zip,
            content_ots,
            "proofs/" + os.path.basename(content_ots),
        )

        # Get final ZIP hashes
        zip_sha = file_util.digest_sha256(final_zip)
        zip_md5 = file_util.digest_md5(final_zip)
        zip_cid = file_util.digest_cidv1(final_zip)

        # Encrypt ZIP, and get those hashes
        aes_key = crypto_util.get_key(action_config["encryption"]["key"])
        enc_zip = os.path.join(archive_dir, content_sha + ".encrypted")
        file_util.encrypt(aes_key, final_zip, enc_zip)

        enc_zip_sha = file_util.digest_sha256(enc_zip)
        enc_zip_md5 = file_util.digest_md5(enc_zip)
        enc_zip_cid = file_util.digest_cidv1(enc_zip)

        # TODO: step 7 and 8

        # Iscn.register_archive(path)

    def create(self, asset_fullpath, jwt_payload, meta):
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
            datetime.datetime.now().strftime("%Y-%m-%d"),
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

    def create_proofmode(self, asset_fullpath, jwt_payload):
        """Process proofmode bundled asset with create action.
        A new asset file is generated in the create-proofmode-output folder with an original creation claim.

        Args:
            asset_fullpath: the local path to the proofmode bundled asset file
            jwt_payload: a JWT payload containing metadata

        Returns:
            the local path to the asset file in the internal directory

        Raises:
            Exception if errors are encountered during processing
        """
        asset_helper = AssetHelper.from_jwt(jwt_payload)
        # Create temporary files to work with.
        tmp_asset_file = asset_helper.get_tmp_file_fullpath(".jpg")
        tmp_claim_file = asset_helper.get_tmp_file_fullpath(".json")

        # TODO: Unzip bundle, store asset file, and create dictionary for claim creation.
        meta_proofmode = None

        # Inject create claim and read back from file.
        claim = _claim.generate_create_proofmode(jwt_payload, meta_proofmode)
        shutil.copy2(asset_fullpath, tmp_asset_file)
        _claim_tool.run_claim_inject(claim, tmp_asset_file, None)
        _claim_tool.run_claim_dump(tmp_asset_file, tmp_claim_file)

        # Copy the C2PA-injected asset to both the internal and shared asset directories.
        internal_asset_file = asset_helper.get_internal_file_fullpath(tmp_asset_file)
        shutil.move(tmp_asset_file, internal_asset_file)
        subfolders = [
            jwt_payload.get("author", {}).get("name"),
            datetime.datetime.now().strftime("%Y-%m-%d"),
        ]
        shutil.copy2(
            internal_asset_file,
            asset_helper.get_assets_create_proofmode_output(subfolders),
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

    def c2pa_add(self, asset_fullpath, org_config, collection_id):
        """Process asset with add action.
        The provided asset file is added to the asset management system and renamed to its internal identifier in the add-output folder.

        Args:
            asset_fullpath: the local path to the asset file
            org_config: configuration dictionary for this organization
            collection_id: string with the unique collection identifier this
                asset is in

        Returns:
            the local path to the asset file in the internal directory
        """
        asset_helper = AssetHelper(org_config.get("id"))
        return self._add(
            asset_fullpath,
            asset_helper.path_for(collection_id, "c2pa-add", output=True),
            asset_helper,
        )

    def c2pa_update(self, asset_fullpath, org_config, collection_id):
        """Process asset with update action.
        A new asset file is generated in the update-output folder with a claim that links it to a parent asset identified by its filename.

        Args:
            asset_fullpath: the local path to the asset file
            org_config: configuration dictionary for this organization
            collection_id: string with the unique collection identifier this
                asset is in

        Returns:
            the local path to the asset file in the internal directory
        """
        organization_id = org_config.get("id")
        asset_helper = AssetHelper(organization_id)
        return self._update(
            asset_fullpath,
            _claim.generate_update(org_config, collection_id),
            asset_helper.path_for(collection_id, "c2pa-update", output=True),
            asset_helper,
        )

    def c2pa_store(self, asset_fullpath, org_config, collection_id):
        """Process asset with store action.
        The provided asset stored on decentralized storage, then a new asset file is generated in the store-output folder with a storage claim.

        Args:
            asset_fullpath: the local path to the asset file
            org_config: configuration dictionary for this organization
            collection_id: string with the unique collection identifier this
                asset is in

        Returns:
            the local path to the asset file in the internal directory
        """
        # Add uploaded asset to the internal directory.
        added_asset = self._add(asset_fullpath, None)

        # Store asset to IPFS and Filecoin.
        ipfs_cid = _filecoin.upload(added_asset)
        _logger.info("Asset file uploaded to IPFS with CID: %s", ipfs_cid)

        organization_id = org_config.get("id")
        return self._update(
            added_asset,
            _claim.generate_store(ipfs_cid.organization_id),
            AssetHelper(organization_id).path_for(
                collection_id, "c2pa-store", output=True
            ),
        )

    def c2pa_custom(self, asset_fullpath, org_config, collection_id):
        """Process asset with custom action.
        A new asset file is generated in the custom-output folder with a claim that links it to a parent asset identified by its filename.

        Args:
            asset_fullpath: the local path to the asset file
            org_config: configuration dictionary for this organization
            collection_id: string with the unique collection identifier this
                asset is in

        Returns:
            the local path to the asset file in the internal directory
        """
        organization_id = org_config.get("id")
        asset_helper = AssetHelper(organization_id)

        # Add uploaded asset to the internal directory.
        added_asset = self._add(asset_fullpath, None)

        # Parse file name to get the search key.
        file_name, _ = os.path.splitext(os.path.basename(added_asset))

        # Find custom assertions for file.
        custom_assertions = self._load_custom_assertions().get(file_name)
        if custom_assertions is None:
            _logger.warning("Could not find custom assertions for asset")
        else:
            _logger.info("Found custom assertions for asset")
        return self._update(
            added_asset,
            _claim.generate_custom(custom_assertions),
            asset_helper.path_for(collection_id, "c2pa-custom", output=True),
            asset_helper,
        )

    def _add(self, asset_fullpath, output_dir, asset_helper):
        # Create temporary files to work with.
        tmp_asset_file = asset_helper.get_tmp_file_fullpath(".jpg")
        time.sleep(1)
        _logger.info("File size: %s", os.path.getsize(asset_fullpath))
        shutil.copy2(asset_fullpath, tmp_asset_file)

        # Copy asset to both the internal and shared asset directories.
        internal_asset_file = asset_helper.get_internal_file_fullpath(tmp_asset_file)
        shutil.move(tmp_asset_file, internal_asset_file)
        if output_dir is not None:
            shutil.copy2(internal_asset_file, output_dir)
        _logger.info("New asset file added: %s", internal_asset_file)

        return internal_asset_file

    def _update(self, asset_fullpath, claim, output_dir, asset_helper):
        # Create temporary files to work with.
        tmp_asset_file = asset_helper.get_tmp_file_fullpath(".jpg")
        tmp_claim_file = asset_helper.get_tmp_file_fullpath(".json")

        # Parse file name to get internal name for parent file.
        file_name, file_extension = os.path.splitext(os.path.basename(asset_fullpath))
        parent_file = os.path.join(
            asset_helper.get_assets_internal(),
            file_name.partition("_")[0].partition("-")[0] + file_extension,
        )

        # Inject update claim and read back from file.
        time.sleep(1)
        _logger.info("File size: %s", os.path.getsize(asset_fullpath))
        shutil.copy2(asset_fullpath, tmp_asset_file)
        _logger.info("Searching for parent file: %s", parent_file)
        if not os.path.isfile(parent_file):
            raise Exception(f"Expected {parent_file} to be a file, but it isn't")

        _logger.info("_update() action found parent file for asset: %s", parent_file)
        _claim_tool.run_claim_inject(claim, tmp_asset_file, parent_file)
        _claim_tool.run_claim_dump(tmp_asset_file, tmp_claim_file)
        # Copy the C2PA-injected asset to both the internal and shared asset directories.
        internal_asset_file = asset_helper.get_internal_file_fullpath(tmp_asset_file)
        shutil.move(tmp_asset_file, internal_asset_file)
        if output_dir is not None:
            shutil.copy2(internal_asset_file, output_dir)
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

    def _load_custom_assertions(self):
        """Loads custom assertions from file.

        Return:
            a dictionary with custom assertions mapped to asset name
        """
        custom_assertions_dictionary = {}
        custom_assertions_path = config.CUSTOM_ASSERTIONS_DICTIONARY
        try:
            with open(custom_assertions_path, "r") as f:
                custom_assertions_dictionary = json.load(f)
                _logger.info(
                    "Successfully loaded custom assertions dictionary: %s",
                    custom_assertions_path,
                )
        except Exception as err:
            _logger.info(
                "No custom assertions dictionary found: %s",
                custom_assertions_path,
            )
        return custom_assertions_dictionary
