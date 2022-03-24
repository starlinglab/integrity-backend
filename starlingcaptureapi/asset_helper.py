import logging

from .file_util import FileUtil
from . import config

import os

_file_util = FileUtil()
_logger = logging.getLogger(__name__)


class AssetHelper:
    """Helpers for management of assets across storage systems."""

    def __init__(self, organization_id):
        """
        Args:
            organization_id: string uniquely representing an organization
                must not contain spaces or special characters, as it will become
                part of directory names (e.g. "hyphacoop" good, not "Hypha Coop")
        """
        if not self._is_filename_safe(organization_id):
            raise ValueError(f"Organization {organization_id} is not filename safe!")
        self.org_id = organization_id

        # Organization-specific directory prefixes
        self.internal_prefix = os.path.join(
            config.INTERNAL_ASSET_STORE, organization_id
        )
        self.shared_prefix = os.path.join(config.SHARED_FILE_SYSTEM, organization_id)

        # Internal directories
        self.dir_internal_assets = os.path.join(self.internal_prefix, "assets")
        self.dir_internal_claims = os.path.join(self.internal_prefix, "claims")
        self.dir_internal_tmp = os.path.join(self.internal_prefix, "tmp")
        self.dir_internal_create = os.path.join(self.internal_prefix, "create")
        self.dir_internal_create_proofmode = os.path.join(
            self.internal_prefix, "create-proofmode"
        )

        # Shared action directories
        self.dir_add = os.path.join(self.shared_prefix, "add")
        self.dir_update = os.path.join(self.shared_prefix, "update")
        self.dir_store = os.path.join(self.shared_prefix, "store")
        self.dir_custom = os.path.join(self.shared_prefix, "custom")

        # Shared output directories
        self.dir_create_output = os.path.join(self.shared_prefix, "create-output")
        self.dir_create_proofmode_output = os.path.join(
            self.shared_prefix, "create-proofmode-output"
        )
        self.dir_add_output = os.path.join(self.shared_prefix, "add-output")
        self.dir_update_output = os.path.join(self.shared_prefix, "update-output")
        self.dir_store_output = os.path.join(self.shared_prefix, "store-output")
        self.dir_custom_output = os.path.join(self.shared_prefix, "custom-output")

    @staticmethod
    def from_jwt(jwt_payload: dict):
        """Initializes an Asset Helper based on the data in the given JWT payload."""
        return AssetHelper(jwt_payload["organization_id"])

    @staticmethod
    def from_filename(filename: str):
        """Initializes an Asset Helper based on the data in the given JWT payload."""
        return AssetHelper(FileUtil.get_organization_id_from_filename(filename))

    def init_dirs(self):
        """Creates the initial directory structure for asset management."""
        _logger.info(f"Initializing internal directories for {self.org_id}")
        _file_util.create_dir(self.dir_internal_assets)
        _file_util.create_dir(self.dir_internal_claims)
        _file_util.create_dir(self.dir_internal_tmp)
        _file_util.create_dir(self.dir_internal_create)
        _file_util.create_dir(self.dir_internal_create_proofmode)

        self._init_collection_dirs()

        _logger.info(f"Initializing legacy action directories for {self.org_id}")
        _file_util.create_dir(self.dir_add)
        _file_util.create_dir(self.dir_store)
        _file_util.create_dir(self.dir_custom)
        _file_util.create_dir(self.dir_create_output)
        _file_util.create_dir(self.dir_create_proofmode_output)
        _file_util.create_dir(self.dir_add_output)
        _file_util.create_dir(self.dir_store_output)
        _file_util.create_dir(self.dir_custom_output)


    def get_assets_internal(self):
        return self.dir_internal_assets

    def get_claims_internal(self):
        return self.dir_internal_claims

    def get_assets_internal_tmp(self):
        return self.dir_internal_tmp

    def get_assets_internal_create(self):
        return self.dir_internal_create

    def get_assets_internal_create_proofmode(self):
        return self.dir_internal_create_proofmode

    def get_assets_add(self):
        return self.dir_add

    def get_assets_store(self):
        return self.dir_store

    def get_assets_custom(self):
        return self.dir_custom

    def get_assets_add_output(self):
        return self.dir_add_output

    def get_assets_create_output(self, subfolders=[]):
        return self._get_path_with_subfolders(
            self.dir_create_output, subfolders=subfolders
        )

    def get_assets_create_proofmode_output(self, subfolders=[]):
        return self._get_path_with_subfolders(
            self.dir_create_proofmode_output, subfolders=subfolders
        )

    def get_assets_store_output(self):
        return self.dir_store_output

    def get_assets_custom_output(self):
        return self.dir_custom_output

    def get_tmp_file_fullpath(self, file_extension):
        return os.path.join(
            self.dir_internal_tmp, _file_util.generate_uuid() + file_extension
        )

    def get_create_file_fullpath(self, from_file):
        _, file_extension = os.path.splitext(from_file)
        return os.path.join(
            self.dir_internal_create,
            _file_util.digest_sha256(from_file) + file_extension,
        )

    def get_create_metadata_fullpath(self, from_file, metadata_tag):
        # TODO: shouldn't have to hash here if we can bundle this with previous func.
        return os.path.join(
            self.dir_internal_create,
            _file_util.digest_sha256(from_file) + "-" + metadata_tag + ".json",
        )

    def get_create_proofmode_file_fullpath(self, from_file):
        _, file_extension = os.path.splitext(from_file)
        return os.path.join(
            self.dir_internal_create_proofmode,
            _file_util.digest_sha256(from_file) + file_extension,
        )

    def get_internal_file_fullpath(self, from_file):
        _, file_extension = os.path.splitext(from_file)
        return os.path.join(
            self.dir_internal_assets,
            _file_util.digest_sha256(from_file) + file_extension,
        )

    def get_internal_claim_fullpath(self, from_file):
        # TODO: shouldn't have to hash here if we can bundle this with previous func.
        return os.path.join(
            self.dir_internal_claims, _file_util.digest_sha256(from_file) + ".json"
        )

    def _shared_collection_prefix(self, collection_id: str):
        return os.path.join(self.shared_prefix, collection_id)

    def path_for(self, collection_id: str, action: str, output: bool = False):
        """Retuns a full directory path for the given collection and action.

        Appends `-output` if output=True.
        """
        return os.path.join(
            self._shared_collection_prefix(collection_id),
            f"{action}-output" if output else action,
        )

    def _filename_safe(self, filename):
        return filename.lower().replace(" ", "-").strip()

    def _get_path_with_subfolders(self, full_path, subfolders=[]):
        """Helper to add subfolders to path, create all directories if needed."""
        for subfolder in subfolders:
            full_path = os.path.join(full_path, self._filename_safe(subfolder))
        _file_util.create_dir(full_path)
        return full_path

    def _init_collection_dirs(self):
        _logger.info(f"Initializing collection directories for {self.org_id}")
        collections = config.ORGANIZATION_CONFIG.get(self.org_id).get("collections")
        if collections == None or len(collections) == 0:
            _logger.info(f"No collections found for {self.org_id}")
            return

        for collection in collections:
            coll_id = collection["id"]
            if not self._is_filename_safe(coll_id):
                raise ValueError(
                    f"Collection {coll_id} for org {self.org_id} is not filename safe"
                )
            for action in collection.get("actions", []):
                action_name = action.get("name")
                _file_util.create_dir(self.path_for(coll_id, action_name))
                _file_util.create_dir(self.path_for(coll_id, action_name, output=True))

    def _is_filename_safe(self, filename):
        return self._filename_safe(filename) == filename
