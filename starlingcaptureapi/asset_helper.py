from .file_util import FileUtil
from . import config

import logging
import os

_file_util = FileUtil()
_logger = logging.getLogger(__name__)

# Internal directories.
dir_internal_assets = os.path.join(config.INTERNAL_ASSET_STORE, "assets")
dir_internal_claims = os.path.join(config.INTERNAL_ASSET_STORE, "claims")
dir_internal_tmp = os.path.join(config.INTERNAL_ASSET_STORE, "tmp")
dir_internal_create = os.path.join(config.INTERNAL_ASSET_STORE, "create")
dir_internal_create_proofmode = os.path.join(
    config.INTERNAL_ASSET_STORE, "create-proofmode"
)

# Shared action directories.
dir_add = os.path.join(config.SHARED_FILE_SYSTEM, "add")
dir_update = os.path.join(config.SHARED_FILE_SYSTEM, "update")
dir_store = os.path.join(config.SHARED_FILE_SYSTEM, "store")
dir_custom = os.path.join(config.SHARED_FILE_SYSTEM, "custom")

# Shared output directories.
dir_create_output = os.path.join(config.SHARED_FILE_SYSTEM, "create-output")
dir_create_proofmode_output = os.path.join(
    config.SHARED_FILE_SYSTEM, "create-proofmode-output"
)
dir_add_output = os.path.join(config.SHARED_FILE_SYSTEM, "add-output")
dir_update_output = os.path.join(config.SHARED_FILE_SYSTEM, "update-output")
dir_store_output = os.path.join(config.SHARED_FILE_SYSTEM, "store-output")
dir_custom_output = os.path.join(config.SHARED_FILE_SYSTEM, "custom-output")


class AssetHelper:
    """Helpers for management of assets across storage systems."""

    def __init__(self, organization_id):
        """
        Args:
            organization_id: string uniquely representing an organization
                must not contain spaces or special characters, as it will become
                part of directory names (e.g. "hyphacoop" good, not "Hypha Coop")
        """
        self.org_id = organization_id

    @staticmethod
    def from_jwt(jwt_payload):
        """Initializes an Asset Helper based on the data in the given JWT payload."""
        return AssetHelper(jwt_payload["organization_id"])

    def init_dirs(self):
        """Creates the initial directory structure for asset management."""
        _file_util.create_dir(dir_internal_assets)
        _file_util.create_dir(dir_internal_claims)
        _file_util.create_dir(dir_internal_tmp)
        _file_util.create_dir(dir_internal_create)
        _file_util.create_dir(dir_internal_create_proofmode)
        _file_util.create_dir(dir_add)
        _file_util.create_dir(dir_update)
        _file_util.create_dir(dir_store)
        _file_util.create_dir(dir_custom)
        _file_util.create_dir(dir_create_output)
        _file_util.create_dir(dir_create_proofmode_output)
        _file_util.create_dir(dir_add_output)
        _file_util.create_dir(dir_update_output)
        _file_util.create_dir(dir_store_output)
        _file_util.create_dir(dir_custom_output)

    def log_dirs(self):
        """Logs the directory structure for asset management."""
        _logger.info("Internal assets directory: %s", self.get_assets_internal())
        _logger.info("Internal claims directory: %s", self.get_claims_internal())
        _logger.info(
            "Internal temporary assets directory: %s", self.get_assets_internal_create()
        )
        _logger.info(
            "Internal assets create directory: %s", self.get_assets_internal_create()
        )
        _logger.info(
            "Internal assets create-proofmode directory: %s",
            self.get_assets_internal_create_proofmode(),
        )
        _logger.info("Shared assets add directory: %s", self.get_assets_add())
        _logger.info("Shared assets update directory: %s", self.get_assets_update())
        _logger.info("Shared assets store directory: %s", self.get_assets_store())
        _logger.info("Shared assets custom directory: %s", self.get_assets_custom())
        _logger.info(
            "Shared assets create output directory: %s", self.get_assets_create_output()
        )
        _logger.info(
            "Shared assets create-proofmode output directory: %s",
            self.get_assets_create_proofmode_output(),
        )
        _logger.info(
            "Shared assets add output directory: %s", self.get_assets_add_output()
        )
        _logger.info(
            "Shared assets update output directory: %s", self.get_assets_update_output()
        )
        _logger.info(
            "Shared assets store output directory: %s", self.get_assets_store_output()
        )
        _logger.info(
            "Shared assets custom output directory: %s", self.get_assets_custom_output()
        )

    def get_assets_internal(self):
        return dir_internal_assets

    def get_claims_internal(self):
        return dir_internal_claims

    def get_assets_internal_tmp(self):
        return dir_internal_tmp

    def get_assets_internal_create(self):
        return dir_internal_create

    def get_assets_internal_create_proofmode(self):
        return dir_internal_create_proofmode

    def get_assets_add(self):
        return dir_add

    def get_assets_update(self):
        return dir_update

    def get_assets_store(self):
        return dir_store

    def get_assets_custom(self):
        return dir_custom

    def get_assets_add_output(self):
        return dir_add_output

    def get_assets_create_output(self, subfolder=None):
        if subfolder:
            dir_subfolder = os.path.join(
                dir_create_output, subfolder.lower().replace(" ", "-")
            )
            _file_util.create_dir(dir_subfolder)
            return dir_subfolder
        return dir_create_output

    def get_assets_create_proofmode_output(self, subfolder=None):
        if subfolder:
            dir_subfolder = os.path.join(
                dir_create_output, subfolder.lower().replace(" ", "-")
            )
            _file_util.create_dir(dir_subfolder)
            return dir_subfolder
        return dir_create_proofmode_output

    def get_assets_update_output(self):
        return dir_update_output

    def get_assets_store_output(self):
        return dir_store_output

    def get_assets_custom_output(self):
        return dir_custom_output

    def get_tmp_file_fullpath(self, file_extension):
        return os.path.join(
            dir_internal_tmp, _file_util.generate_uuid() + file_extension
        )

    def get_create_file_fullpath(self, from_file):
        _, file_extension = os.path.splitext(from_file)
        return os.path.join(
            dir_internal_create, _file_util.digest_sha256(from_file) + file_extension
        )

    def get_create_metadata_fullpath(self, from_file, metadata_tag):
        # TODO: shouldn't have to hash here if we can bundle this with previous func.
        return os.path.join(
            dir_internal_create,
            _file_util.digest_sha256(from_file) + "-" + metadata_tag + ".json",
        )

    def get_create_proofmode_file_fullpath(self, from_file):
        _, file_extension = os.path.splitext(from_file)
        return os.path.join(
            dir_internal_create_proofmode,
            _file_util.digest_sha256(from_file) + file_extension,
        )

    def get_internal_file_fullpath(self, from_file):
        _, file_extension = os.path.splitext(from_file)
        return os.path.join(
            dir_internal_assets, _file_util.digest_sha256(from_file) + file_extension
        )

    def get_internal_claim_fullpath(self, from_file):
        # TODO: shouldn't have to hash here if we can bundle this with previous func.
        return os.path.join(
            dir_internal_claims, _file_util.digest_sha256(from_file) + ".json"
        )
