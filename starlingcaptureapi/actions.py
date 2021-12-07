from asset_helper import AssetHelper
from claim import Claim
from claim_tool import ClaimTool
from filecoin import Filecoin

import logging
import os
import shutil

_asset_helper = AssetHelper()
_claim = Claim()
_claim_tool = ClaimTool()
_filecoin = Filecoin()
_logger = logging.getLogger(__name__)


class Actions:
    """Actions for processing assets."""

    def create(self, asset_fullpath, jwt_payload, meta):
        """Process asset with create action.
        A new asset file is generated in the create-output folder with an original creation claim.

        Args:
            asset_fullpath: the local path to the asset file
            jwt_payload: a JWT payload containing metadata
            meta: dictionary with the 'meta' section of the incoming multipart request
        """
        # Create temporary files to work with.
        tmp_asset_file = _asset_helper.get_tmp_file_fullpath(".jpg")
        tmp_claim_file = _asset_helper.get_tmp_file_fullpath(".json")

        # Inject create claim and read back from file.
        claim = _claim.generate_create(jwt_payload, meta)
        shutil.copy2(asset_fullpath, tmp_asset_file)
        if _claim_tool.run_claim_inject(claim, tmp_asset_file, None):
            if _claim_tool.run_claim_dump(tmp_asset_file, tmp_claim_file):
                # Copy the C2PA-injected asset to both the internal and shared asset directories.
                internal_asset_file = _asset_helper.get_internal_file_fullpath(
                    tmp_asset_file
                )
                shutil.move(tmp_asset_file, internal_asset_file)
                shutil.copy2(
                    internal_asset_file, _asset_helper.get_assets_create_output()
                )
                _logger.info(
                    "New asset file added to the internal and shared assets directories: %s",
                    internal_asset_file,
                )
                internal_claim_file = _asset_helper.get_internal_claim_fullpath(
                    internal_asset_file
                )
                shutil.move(tmp_claim_file, internal_claim_file)
                _logger.info(
                    "New claim file added to the internal claims directory: %s",
                    internal_claim_file,
                )
                return
        _logger.error(
            "Failed to process asset with the create action: %s", asset_fullpath
        )

    def add(self, asset_fullpath):
        """Process asset with add action.
        The provided asset file is added to the asset management system and renamed to its internal identifier in the add-output folder.

        Args:
            asset_fullpath: the local path to the asset file
        """
        # Copy asset to both the internal and shared asset directories.
        internal_file = _asset_helper.get_internal_file_fullpath(asset_fullpath)
        shutil.move(asset_fullpath, internal_file)
        shutil.copy2(internal_file, _asset_helper.get_assets_add_output())
        _logger.info(
            "New file added to the internal and shared assets directories: %s",
            internal_file,
        )
        # TODO(ben): handle file errors

    def update(self, asset_fullpath):
        """Process asset with update action.
        A new asset file is generated in the update-output folder with a claim that links it to a parent asset identified by its filename.

        Args:
            asset_fullpath: the local path to the asset file
        """
        # Create temporary files to work with.
        tmp_asset_file = _asset_helper.get_tmp_file_fullpath(".jpg")
        tmp_claim_file = _asset_helper.get_tmp_file_fullpath(".json")

        # Parse file name to get internal name for parent file.
        file_name, file_extension = os.path.splitext(os.path.basename(asset_fullpath))
        parent_file = os.path.join(
            _asset_helper.get_assets_internal(),
            file_name.partition("_")[0].partition("-")[0] + file_extension,
        )

        # Inject update claim and read back from file.
        claim = _claim.generate_update()
        shutil.copy2(asset_fullpath, tmp_asset_file)
        _logger.info("Searching for parent file: %s", parent_file)
        if os.path.isfile(parent_file):
            _logger.info("Update action found parent file for asset: %s", parent_file)
            if _claim_tool.run_claim_inject(claim, tmp_asset_file, parent_file):
                if _claim_tool.run_claim_dump(tmp_asset_file, tmp_claim_file):
                    # Copy the C2PA-injected asset to both the internal and shared asset directories.
                    internal_asset_file = _asset_helper.get_internal_file_fullpath(
                        tmp_asset_file
                    )
                    shutil.move(tmp_asset_file, internal_asset_file)
                    shutil.copy2(
                        internal_asset_file, _asset_helper.get_assets_update_output()
                    )
                    _logger.info(
                        "New asset file added to the internal and shared assets directories: %s",
                        internal_asset_file,
                    )
                    internal_claim_file = _asset_helper.get_internal_claim_fullpath(
                        internal_asset_file
                    )
                    shutil.move(tmp_claim_file, internal_claim_file)
                    _logger.info(
                        "New claim file added to the internal claims directory: %s",
                        internal_claim_file,
                    )
                    return
            _logger.error(
                "Failed to process asset with the update action: %s", asset_fullpath
            )
        else:
            _logger.error(
                "Update action found no parent file for asset: %s", asset_fullpath
            )

    def store(self, asset_fullpath):
        """Process asset with store action.
        The provided asset stored on decentralized storage, then a new asset file is generated in the store-output folder with a storage claim.

        Args:
            asset_fullpath: the local path to the asset file
        """
        # Store asset to IPFS and Filecoin.
        ipfs_cid = _filecoin.upload(asset_fullpath)
        _logger.info("Asset file uploaded to IPFS with CID: %s", ipfs_cid)

        # TODO: This will always be None at this point. Here only for demonstration purposes.
        # maybe_pieceCid = _filecoin.get_status(cid)
        # _logger.info(f"PieceCID: {maybe_pieceCid}")

        # Create temporary files to work with.
        tmp_asset_file = _asset_helper.get_tmp_file_fullpath(".jpg")
        tmp_claim_file = _asset_helper.get_tmp_file_fullpath(".json")

        # Parse file name to get internal name for parent file.
        file_name, file_extension = os.path.splitext(os.path.basename(asset_fullpath))
        parent_file = os.path.join(
            _asset_helper.get_assets_internal(),
            file_name.partition("_")[0].partition("-")[0] + file_extension,
        )

        # Inject store claim and read back from file.
        claim = _claim.generate_store(ipfs_cid)
        shutil.copy2(asset_fullpath, tmp_asset_file)
        _logger.info("Searching for parent file: %s", parent_file)
        if os.path.isfile(parent_file):
            _logger.info("Store action found parent file for asset: %s", parent_file)
            if _claim_tool.run_claim_inject(claim, tmp_asset_file, parent_file):
                if _claim_tool.run_claim_dump(tmp_asset_file, tmp_claim_file):
                    # Copy the C2PA-injected asset to both the internal and shared asset directories.
                    internal_asset_file = _asset_helper.get_internal_file_fullpath(
                        tmp_asset_file
                    )
                    shutil.move(tmp_asset_file, internal_asset_file)
                    shutil.copy2(
                        internal_asset_file, _asset_helper.get_assets_store_output()
                    )
                    _logger.info(
                        "New asset file added to the internal and shared assets directories: %s",
                        internal_asset_file,
                    )
                    internal_claim_file = _asset_helper.get_internal_claim_fullpath(
                        internal_asset_file
                    )
                    shutil.move(tmp_claim_file, internal_claim_file)
                    _logger.info(
                        "New claim file added to the internal claims directory: %s",
                        internal_claim_file,
                    )
                    return
            _logger.error(
                "Failed to process asset with the store action: %s", asset_fullpath
            )
        else:
            _logger.error(
                "Store action found no parent file for asset: %s", asset_fullpath
            )
