from asset_helper import AssetHelper
from claim import Claim
from claim_tool import ClaimTool

import logging
import shutil

_asset_helper = AssetHelper()
_claim = Claim()
_claim_tool = ClaimTool()
_logger = logging.getLogger(__name__)


class Actions:
    """Actions for processing assets."""

    def create(self, asset_fullpath, jwt_payload):
        """Process asset with create action.
        A new asset file is generated in the create-output folder with an original creation claim.

        Args:
            asset_fullpath: the local path to the asset file
            jwt_payload: a JWT payload containing metadata
        """
        # Create temporary files to work with.
        tmp_asset_file = _asset_helper.get_tmp_file_fullpath(".jpg")
        tmp_claim_file = _asset_helper.get_tmp_file_fullpath(".json")

        # Inject create claim and read back from file.
        claim = _claim.generate_create(jwt_payload)
        shutil.copy2(asset_fullpath, tmp_asset_file)
        if _claim_tool.run_claim_inject(claim, tmp_asset_file, None):
            if _claim_tool.run_claim_dump(tmp_asset_file, tmp_claim_file):
                # Copy the C2PA-injected asset to both the internal and shared asset directories.
                internal_file = _asset_helper.get_internal_file_fullpath(tmp_asset_file)
                shutil.move(tmp_asset_file, internal_file)
                shutil.copy2(internal_file, _asset_helper.get_assets_create_output())
                _logger.info(
                    "New file added to the internal and shared assets directories: %s",
                    internal_file
                )
                return
        _logger.error(
            "Failed to process asset with the create action: %s",
            asset_fullpath
        )

    def add(self, asset_fullpath):
        """Process asset with add action.
        The provided asset file is added to the asset management system and renamed to its internal identifier in the add-output folder.

        Args:
            asset_fullpath: the local path to the asset file
        """
        _logger.error(
            "Failed to process asset with the add action: %s",
            asset_fullpath
        )

    def update(self, asset_fullpath):
        """Process asset with update action.
        A new asset file is generated in the update-output folder with a claim that links it to a parent asset identified by its filename.

        Args:
            asset_fullpath: the local path to the asset file
        """
        _logger.error(
            "Failed to process asset with the update action: %s",
            asset_fullpath
        )

    def store(self, asset_fullpath):
        """Process asset with store action.
        The provided asset stored on decentralized storage, then a new asset file is generated in the store-output folder with a storage claim.

        Args:
            asset_fullpath: the local path to the asset file
        """
        _logger.error(
            "Failed to process asset with the store action: %s",
            asset_fullpath
        )