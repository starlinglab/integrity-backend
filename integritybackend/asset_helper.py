from . import config
from .file_util import FileUtil
from .log_helper import LogHelper

import os

_file_util = FileUtil()
_logger = LogHelper.getLogger()


class AssetHelper:
    """Helpers for management of asset file paths.

    Directory structure overview:

    * config.INTERNAL_ASSET_STORE
        `-- organization_id
            |-- tmp
            `-- collection_id
                |-- input
                |-- action-name-0
                |-- ...
                `-- action-name-N

      - internal-only directory tree
      - organized by organization, by collection, and by action
      - includes assets for permanent storage, and also temporary directories
        for intermediate working files

    * config.SHARED_FILE_SYSTEM
        `-- organization_id
            `-- collection_id
                |-- action-name-0
                |-- ...
                `-- action-name-N

      - directory tree that is used to share action outputs with external clients
      - organized by organization, by collection, and by action
      - action-specific folders might be further organized as relevant for that
        action; for example, the output of the c2pa-starling-capture create action
        is organized by author name and date
    """

    def __init__(self, organization_id):
        """
        Args:
            organization_id: string uniquely representing an organization
                must not contain spaces or special characters, as it will become
                part of directory names (e.g. "starlinglab" good, not "Starling Lab")
        """
        if not self.is_filename_safe(organization_id):
            raise ValueError(f"Organization {organization_id} is not filename safe!")
        self.org_id = organization_id

        # Organization-specific directory prefixes
        self.internal_prefix = os.path.join(
            config.INTERNAL_ASSET_STORE, organization_id
        )
        self.shared_prefix = os.path.join(config.SHARED_FILE_SYSTEM, organization_id)
        self.dir_internal_tmp = os.path.join(self.internal_prefix, "tmp")

    @staticmethod
    def from_jwt(jwt_payload: dict):
        """Initializes an Asset Helper based on the data in the given JWT payload."""
        return AssetHelper(jwt_payload["organization_id"])

    @staticmethod
    def from_filename(filename: str):
        """Initializes an Asset Helper based on the data in the given filename."""
        return AssetHelper(FileUtil.get_organization_id_from_filename(filename))

    def init_dirs(self):
        """Creates the initial directory structure for asset management."""
        _logger.info(f"Initializing internal directories for {self.org_id}")
        _file_util.create_dir(self.dir_internal_tmp)
        self._init_collection_dirs()

    def get_tmp_file_fullpath(self, file_extension):
        return os.path.join(
            self.dir_internal_tmp, _file_util.generate_uuid() + file_extension
        )

    # def get_create_file_fullpath(self, from_file):
    #     _, file_extension = os.path.splitext(from_file)
    #     return os.path.join(
    #         self.dir_internal_create,
    #         _file_util.digest_sha256(from_file) + file_extension,
    #     )

    # def get_create_metadata_fullpath(self, from_file, metadata_tag):
    #     # TODO: shouldn't have to hash here if we can bundle this with previous func.
    #     return os.path.join(
    #         self.dir_internal_create,
    #         _file_util.digest_sha256(from_file) + "-" + metadata_tag + ".json",
    #     )

    # def get_create_proofmode_file_fullpath(self, from_file):
    #     _, file_extension = os.path.splitext(from_file)
    #     return os.path.join(
    #         self.dir_internal_create_proofmode,
    #         _file_util.digest_sha256(from_file) + file_extension,
    #     )

    def get_internal_file_fullpath(self, from_file):
        _, file_extension = os.path.splitext(from_file)
        return os.path.join(
            self.dir_internal_assets,
            _file_util.digest_sha256(from_file) + file_extension,
        )

    # def get_internal_claim_fullpath(self, from_file):
    #     # TODO: shouldn't have to hash here if we can bundle this with previous func.
    #     return os.path.join(
    #         self.dir_internal_claims, _file_util.digest_sha256(from_file) + ".json"
    #     )

    # def legacy_path_for(self, action_name: str, output: bool = False) -> str:
    #     """Returns a full directory path for the given action."""
    #     return os.path.join(
    #         self.shared_prefix,
    #         f"{action_name}-output" if output else action_name,
    #     )

    def path_for_input(self, collection_id: str) -> str:
        """Returns a full direction path for the input dir for this collection."""
        return os.path.join(self._collection_prefix(collection_id), "input")

    def path_for_action(self, collection_id: str, action_name: str):
        """Retuns a full directory path for the given collection and action."""
        return os.path.join(
            self._collection_prefix(collection_id), f"action-{action_name}"
        )

    def path_for_action_output(self, collection_id: str, action_name: str):
        """Retuns a full directory path for the output dir of the given collection and action."""
        return os.path.join(self.shared_prefix, collection_id, f"action-{action_name}")

    def path_for_action_tmp(self, collection_id: str, action_name: str):
        """Retuns a full directory path for the tmp dir of the given collection and action."""
        return os.path.join(
            self.dir_internal_tmp, collection_id, f"action-{action_name}"
        )

    def filename_safe(self, filename):
        return filename.lower().replace(" ", "-").strip()

    def is_filename_safe(self, filename):
        return self.filename_safe(filename) == filename

    def _collection_prefix(self, collection_id: str) -> str:
        return os.path.join(self.internal_prefix, collection_id)

    def _init_collection_dirs(self):
        _logger.info(f"Initializing collection directories for {self.org_id}")
        collections_dict = config.ORGANIZATION_CONFIG.get(self.org_id).get(
            "collections", {}
        )
        if len(collections_dict.keys()) == 0:
            _logger.info(f"No collections found for {self.org_id}")
            return

        for coll_id, coll_config in collections_dict.items():
            if not self.is_filename_safe(coll_id):
                raise ValueError(
                    f"Collection {coll_id} for org {self.org_id} is not filename safe"
                )
            _file_util.create_dir(self.path_for_input(coll_id))
            for action_name in coll_config.get("actions", {}).keys():
                _file_util.create_dir(self.path_for_action(coll_id, action_name))
                _file_util.create_dir(self.path_for_action_output(coll_id, action_name))
                _file_util.create_dir(self.path_for_action_tmp(coll_id, action_name))
