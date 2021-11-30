from file_util import FileUtil

import config
import logging
import os

_file_util = FileUtil()
_logger = logging.getLogger(__name__)

dir_internal_assets = os.path.join(config.INTERNAL_ASSET_STORE, "assets")
dir_internal_tmp = os.path.join(config.INTERNAL_ASSET_STORE, "tmp")
dir_internal_create = os.path.join(config.INTERNAL_ASSET_STORE, "create")
dir_update = os.path.join(config.SHARED_FILE_SYSTEM, "update")
dir_store = os.path.join(config.SHARED_FILE_SYSTEM, "store")

class AssetHelper:
    """Helpers for management of assets across storage systems."""

    def init_dirs(self):
        """Creates the initial directory structure for asset management."""
        if _file_util.create_dir(dir_internal_assets):
            _logger.info("Created internal assets directory: " + dir_internal_assets)
        if _file_util.create_dir(dir_internal_tmp):
            _logger.info("Created internal temporary assets directory: " + dir_internal_tmp)
        if _file_util.create_dir(dir_internal_create):
            _logger.info("Created internal assets creation directory: " + dir_internal_create)
        if _file_util.create_dir(dir_update):
            _logger.info("Created shared assets update directory: " + dir_update)
        if _file_util.create_dir(dir_store):
            _logger.info("Created shared assets store directory: " + dir_store)


    def get_assets_internal(self):
        return dir_internal_assets


    def get_assets_internal_tmp(self):
        return dir_internal_tmp


    def get_assets_internal_create(self):
        return dir_internal_create


    def get_assets_update(self):
        return dir_update


    def get_assets_store(self):
        return dir_store


    def get_assets_shared(self):
        return config.SHARED_FILE_SYSTEM


    def get_tmp_file_fullpath(self, file_extension):
        return os.path.join(dir_internal_tmp, _file_util.generate_uuid() + file_extension)


    def get_create_file_fullpath(self, from_file):
        file_name, file_extension = os.path.splitext(from_file);
        return os.path.join(dir_internal_create, _file_util.digest_sha256(from_file) + file_extension)


    def get_internal_file_fullpath(self, from_file):
        file_name, file_extension = os.path.splitext(from_file);
        return os.path.join(dir_internal_assets, _file_util.digest_sha256(from_file) + file_extension)


    def digest_sha256(self, file_path):
        """Generates SHA-256 digest of a file.

        Args:
            file_path: the local path to a file

        Returns:
            the HEX-encoded SHA-256 digest of the input file
        """
        hasher = sha256()
        with open(file_path, "rb") as f:
            # Parse file in blocks
            for byte_block in iter(lambda: f.read(4096), b""):
                hasher.update(byte_block)
            return hasher.hexdigest()
        # TODO: handle error (image not found, etc.)
