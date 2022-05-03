from . import config
from .file_util import FileUtil
from .log_helper import LogHelper

import os

_file_util = FileUtil()
_logger = LogHelper.getLogger()


class AssetHelper:
    """Helpers for management of asset file paths.

    Directory structure overview:
    * config.INTERNAL_ASSET_STORE:
      - internal-only directory tree
      - used for both input and output location of assets (i.e. files) that we
        execute actions on
      - organized by organization, by collection and by action
      - includes assets for permanent storage, and also temporary directories
        for intermediate working files
      - some legacy action folders are still in use, which are not organized by
        collection
    * config.SHARED_FILE_SYSTEM
      - directory tree that is shared with external clients
      - used for both input and output location of assets (i.e. files) that we
        execute actions on
      - organized per organization
      - action-specific folders might be further organized as relevant for that
        action; for example, the output of the create action is organized by
        author name and date
      - some legacy action folders are still in use, which are not organized by
        collection

    Example directory trees:

    assets_dir
    `-- hyphacoop-org
        |-- tmp
        # |-- assets (legacy)
        # |-- claims (legacy)
        # |-- create (legacy)
        # |-- create-proofmode (legacy)
        `-- mycelium-collection
            |-- input
            `-- action-archive

    shared_dir
    `-- hyphacoop-org
        # |-- add  # legacy path, deprecated in favor of per-collection directories
        # |-- add-output # legacy path, deprecated in favor of per-collection directories
    """

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
        # self.dir_internal_assets = os.path.join(self.internal_prefix, "assets")
        # self.dir_internal_claims = os.path.join(self.internal_prefix, "claims")
        self.dir_internal_tmp = os.path.join(self.internal_prefix, "tmp")
        # self.dir_internal_create = os.path.join(self.internal_prefix, "create")
        # self.dir_internal_create_proofmode = os.path.join(
        #     self.internal_prefix, "create-proofmode"
        # )

        # Legacy shared output directories (not collection-specific)
        # self.dir_create_output = os.path.join(self.shared_prefix, "create-output")
        # self.dir_create_proofmode_output = os.path.join(
        #     self.shared_prefix, "create-proofmode-output"
        # )

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
        # _file_util.create_dir(self.dir_internal_assets)
        # _file_util.create_dir(self.dir_internal_claims)
        _file_util.create_dir(self.dir_internal_tmp)
        # _file_util.create_dir(self.dir_internal_create)
        # _file_util.create_dir(self.dir_internal_create_proofmode)

        self._init_collection_dirs()

        _logger.info(f"Initializing legacy action directories for {self.org_id}")
        # 'Create' files come via HTTP, there are no "input" create folders
        # _file_util.create_dir(self.legacy_path_for("create", output=True))
        # _file_util.create_dir(self.legacy_path_for("create-proofmode", output=True))

    def get_assets_internal(self):
        return self.dir_internal_assets

    # def get_assets_create_output(self, subfolders=[]):
    #     return self._get_path_with_subfolders(
    #         self.dir_create_output, subfolders=subfolders
    #     )

    # def get_assets_create_proofmode_output(self, subfolders=[]):
    #     return self._get_path_with_subfolders(
    #         self.dir_create_proofmode_output, subfolders=subfolders
    #     )

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

    def input_path_for(self, collection_id: str) -> str:
        """Returns a full direction path for the input dir for this collection."""
        return os.path.join(self._collection_prefix(collection_id), "input")

    def path_for(self, collection_id: str, action_name: str, output: bool = False):
        """Retuns a full directory path for the given collection and action.

        Appends `-output` if output=True.
        """
        return os.path.join(
            self._collection_prefix(collection_id),
            f"action-{action_name}-output" if output else f"action-{action_name}",
        )

    def get_action_dir(self, collection_id, action_name):
        return os.path.join(self.internal_prefix, collection_id, f"action-{action_name}")

    def get_tmp_action_dir(self, collection_id, action_name):
        return os.path.join(self.dir_internal_tmp, collection_id, f"action-{action_name}")

    def _collection_prefix(self, collection_id: str) -> str:
        return os.path.join(self.internal_prefix, collection_id)

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
        collections_dict = config.ORGANIZATION_CONFIG.get(self.org_id).get(
            "collections", {}
        )
        if len(collections_dict.keys()) == 0:
            _logger.info(f"No collections found for {self.org_id}")
            return

        for coll_id, coll_config in collections_dict.items():
            if not self._is_filename_safe(coll_id):
                raise ValueError(
                    f"Collection {coll_id} for org {self.org_id} is not filename safe"
                )
            _file_util.create_dir(self.input_path_for(coll_id))
            for action_name in coll_config.get("actions", {}).keys():
                # This input path is a legacy path, and will be removed when all actions
                # move to use the per-collection input directory
                _file_util.create_dir(self.path_for(coll_id, action_name))
                _file_util.create_dir(self.path_for(coll_id, action_name, output=True))

    def _is_filename_safe(self, filename):
        return self._filename_safe(filename) == filename
