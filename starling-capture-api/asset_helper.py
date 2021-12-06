from file_util import FileUtil

import config
import logging
import os

_file_util = FileUtil()
_logger = logging.getLogger(__name__)

# Internal directories.
dir_internal_assets = os.path.join(config.INTERNAL_ASSET_STORE, "assets")
dir_internal_claims = os.path.join(config.INTERNAL_ASSET_STORE, "claims")
dir_internal_tmp = os.path.join(config.INTERNAL_ASSET_STORE, "tmp")
dir_internal_create = os.path.join(config.INTERNAL_ASSET_STORE, "create")

# Shared action directories.
dir_add = os.path.join(config.SHARED_FILE_SYSTEM, "add")
dir_update = os.path.join(config.SHARED_FILE_SYSTEM, "update")
dir_store = os.path.join(config.SHARED_FILE_SYSTEM, "store")

# Shared output directories.
dir_create_output = os.path.join(config.SHARED_FILE_SYSTEM, "create-output")
dir_add_output = os.path.join(config.SHARED_FILE_SYSTEM, "add-output")
dir_update_output = os.path.join(config.SHARED_FILE_SYSTEM, "update-output")
dir_store_output = os.path.join(config.SHARED_FILE_SYSTEM, "store-output")

class AssetHelper:
    """Helpers for management of assets across storage systems."""

    def init_dirs(self):
        """Creates the initial directory structure for asset management."""
        if _file_util.create_dir(dir_internal_assets):
            _logger.info("Created internal assets directory: " + dir_internal_assets)
        if _file_util.create_dir(dir_internal_claims):
            _logger.info("Created internal claims directory: " + dir_internal_claims)
        if _file_util.create_dir(dir_internal_tmp):
            _logger.info("Created internal temporary assets directory: " + dir_internal_tmp)
        if _file_util.create_dir(dir_internal_create):
            _logger.info("Created internal assets create directory: " + dir_internal_create)
        if _file_util.create_dir(dir_add):
            _logger.info("Created shared assets add directory: " + dir_add)
        if _file_util.create_dir(dir_update):
            _logger.info("Created shared assets update directory: " + dir_update)
        if _file_util.create_dir(dir_store):
            _logger.info("Created shared assets store directory: " + dir_store)
        if _file_util.create_dir(dir_create_output):
            _logger.info("Created shared assets create output directory: " + dir_create_output)
        if _file_util.create_dir(dir_add_output):
            _logger.info("Created shared assets add output directory: " + dir_add_output)
        if _file_util.create_dir(dir_update_output):
            _logger.info("Created shared assets update output directory: " + dir_update_output)
        if _file_util.create_dir(dir_store_output):
            _logger.info("Created shared assets store output directory: " + dir_store_output)

    def log_dirs(self):
        """Logs the directory structure for asset management."""
        _logger.info("Internal assets directory: %s", self.get_assets_internal())
        _logger.info("Internal claims directory: %s", self.get_claims_internal())
        _logger.info("Internal temporary assets directory: %s", self.get_assets_internal_create())
        _logger.info("Internal assets create directory: %s", self.get_assets_internal_create())
        _logger.info("Shared assets add directory: %s", self.get_assets_add())
        _logger.info("Shared assets update directory: %s", self.get_assets_update())
        _logger.info("Shared assets store directory: %s", self.get_assets_store())
        _logger.info("Shared assets create output directory: %s", self.get_assets_create_output())
        _logger.info("Shared assets add output directory: %s", self.get_assets_add_output())
        _logger.info("Shared assets update output directory: %s", self.get_assets_update_output())
        _logger.info("Shared assets store output directory: %s", self.get_assets_store_output())

    def get_assets_internal(self):
        return dir_internal_assets

    def get_claims_internal(self):
        return dir_internal_claims

    def get_assets_internal_tmp(self):
        return dir_internal_tmp

    def get_assets_internal_create(self):
        return dir_internal_create

    def get_assets_add(self):
        return dir_add

    def get_assets_update(self):
        return dir_update

    def get_assets_store(self):
        return dir_store

    def get_assets_add_output(self):
        return dir_add_output

    def get_assets_create_output(self):
        return dir_create_output

    def get_assets_update_output(self):
        return dir_update_output

    def get_assets_store_output(self):
        return dir_store_output

    def get_tmp_file_fullpath(self, file_extension):
        return os.path.join(dir_internal_tmp, _file_util.generate_uuid() + file_extension)

    def get_create_file_fullpath(self, from_file):
        _, file_extension = os.path.splitext(from_file)
        return os.path.join(dir_internal_create, _file_util.digest_sha256(from_file) + file_extension)

    def get_internal_file_fullpath(self, from_file):
        _, file_extension = os.path.splitext(from_file)
        return os.path.join(dir_internal_assets, _file_util.digest_sha256(from_file) + file_extension)

    def get_internal_claim_fullpath(self, from_file):
        # TODO: shouldn't have to hash here if we can bundle this with previous func.
        return os.path.join(dir_internal_claims, _file_util.digest_sha256(from_file) + ".json")
