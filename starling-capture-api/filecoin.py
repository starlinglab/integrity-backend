import config
import os
import requests

_WEB3_STORAGE_BASE_URL = "https://api.web3.storage"
_UPLOAD_URL = f"{_WEB3_STORAGE_BASE_URL}/upload"
_STATUS_URL = f"{_WEB3_STORAGE_BASE_URL}/status"


class Filecoin:
    """Handles interactions with IPFS and Filecoin"""

    def __init__(self):
        self.auth_header = {
            "Authorization": f"Bearer {config.WEB3_STORAGE_API_TOKEN}"
        }

    def upload(self, file_path):
        """Uploads a file.

        Args:
            file_path: the full path to the file to upload

        Returns:
            cid of the uploaded file
        """
        # TODO: figure out what filename we want to give for the upload -- just the last part of the filename?
        files = {
            "file": (
                os.path.basename(file_path),
                open(file_path, "rb"),
                "application/octet-stream",
            )
        }
        response = requests.post(_UPLOAD_URL, headers=self.auth_header, files=files)
        # TODO: add error handling
        return response.json()["cid"]

    def get_status(self, cid):
        """Gets Filecoin deals status for a CID

        Args:
            cid: the cid we want to check status for

        Returns:
            Filecoin Piece ID, if there is one; None otherwise
        """
        response = requests.get(f"{_STATUS_URL}/{cid}", headers=self.auth_header)
        status_json = response.json()
        print(f"Status for CID {cid}: {status_json}")
        if len(status_json["deals"]) > 0:
            return status_json["deals"][0]["pieceCid"]
        else:
            return None

