import os
from .asset_helper import AssetHelper
from .file_util import FileUtil


class EncryptedArchive:
    """Based on a metadata file, handles zipping, encryption and CID creation."""

    def __init__(self, asset_meta_path: str):
        self.meta_path = asset_meta_path
        self.asset_helper = AssetHelper.from_filename(self.meta_path)

        self.archive_path = None
        self.asset_hash = None
        self.cid = None
        self.recorded_content_cid = None
        self.zip_archive_cid = None

    @staticmethod
    def make_from_meta(asset_meta_path):
        """Creates an encrypted zip for archival, based on the given metadata file.

        Args:
            asset_meta_path: full local path to metadata JSON file for the asset to zip and encrypt

        Return:
            an instance of EncryptedArchive with paths to archival files and CIDs for various things
        """
        archive = EncryptedArchive(asset_meta_path)
        archive.make()
        return archive

    def make(self):
        """Creates an encrypted zip for archival, based on the this archive's self.meta_path file.

        Sketch of what this method does (some of the steps might be better in a different order):
        1. Collect all the files needed for the zip, based on the hash in the `self.meta_path` filename
-       2. Zip ALL the files from step #1
        3. Encrypt the zip from step #2
        4. Compute CIDs for recorded content, zip and encrypted zip
        5. Set a bunch of properties with this data, so that they can be retrieved later:
            self.path : full path of encrypted archive file
            self.recorded_content_cid : CID of the Recorded Content file
            self.zip_archive_cid : CID of the unencrypted ZIP archive file
            self.cid : CID of the encrypted archive file
        """
        self.asset_hash = FileUtil.get_hash_from_filename(self.meta_path)
        FileUtil.make_zip(self._asset_files, self._zip_filename)
        # TODO: encrypt self._zip_filename
        # TODO: compute CIDs

    def _zip_filename(self):
        os.path.join(self.asset_helper.dir_internal_tmp, f"{self.asset_hash}.zip")

    def _asset_files(self):
        directory = os.path.dirname(self.meta_path)
        [
            self.meta_path,
            os.path.join(directory, f"{self.asset_hash}-signature.json")  # made up example, FIXME
            # TODO: figure out which files should go here -- do we have a set of name patterns that we expect?
            #       or should we be looking for all the files in `directory` that contain `hash` in the filenam?
        ]
