from .file_util import FileUtil


class EncryptedArchive:
    """Based on a metadata file, handles zipping, encryption and CID creation."""

    def __init__(self, asset_meta_path: str):
        self.meta_path = asset_meta_path

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

        1. Collect all the files needed for the zip, based on the hash in the `self.meta_path` filename
        2. Zip ALL the files from step #1
        3. Encrypt the zip from step #2
        4. Compute CIDs for recorded content, zip and encrypted zip
        5. Set a bunch of properties with this data, so that they can be retrieved later:
            self.path : full path of encrypted archive file
            self.recorded_content_cid : CID of the Recorded Content file
            self.zip_archive_cid : CID of the unencrypted ZIP archive file
            self.cid : CID of the encrypted archive file
        """
        self.asset_hash = FileUtil.get_hash_from_filename(self.meta_path)
        pass
