from .asset_helper import AssetHelper

import json
import logging
import shutil

_logger = logging.getLogger(__name__)


class Multipart:
    """Handles incoming multi-part requests."""
    def __init__(self, request):
        self.request = request
        self.asset_helper = AssetHelper.from_jwt(self.request.get("jwt_payload"))

    async def read(self):
        """Reads the multipart section of an incoming request and handles it appropriately.

        Assumes that we will _not_ receive nested multi-parts.

        If it encounters a part with Content-Disposition including name=file, it will store this
        file in our local config.IMAGES_DIR for future processing.

        TODO: read JSON parts into memory and return them

        Args:
            request: an aiohttp request containing multipart data

        Returns:
            a dictionary with metadata about the multipart sections encountered
        """
        multipart_data = {}
        reader = await self.request.multipart()
        part = None
        asset_file = None
        while True:
            part = await reader.next()
            if part is None:
                # No more parts, we're done reading.
                break
            if part.name == "file":
                asset_file = multipart_data["asset_fullpath"] = await self._write_file(
                    part, self.request.path
                )
            elif part.name == "meta":
                multipart_data["meta"] = await part.json()
                if asset_file is not None:
                    await self._write_json(multipart_data["meta"], asset_file, "meta")
            elif part.name == "signature":
                multipart_data["signature"] = await part.json()
                if asset_file is not None:
                    await self._write_json(
                        multipart_data["signature"], asset_file, "signature"
                    )
            else:
                _logger.warning("Ignoring multipart part %s", part.name)
        return multipart_data

    async def _write_file(self, part, request_path):
        # Write file in temporary directory.
        tmp_file = self.asset_helper.get_tmp_file_fullpath(".jpg")

        # Mode "x" will throw an error if a file with the same name already exists.
        with open(tmp_file, "xb") as f:
            while True:
                chunk = await part.read_chunk()
                if not chunk:
                    # No more chunks, done reading this part.
                    break
                f.write(chunk)

        # Move completed file over to assets creation directory.
        if request_path == "/v1/assets/create-proofmode":
            create_file = self.asset_helper.get_create_proofmode_file_fullpath(tmp_file)
        else:
            create_file = self.asset_helper.get_create_file_fullpath(tmp_file)
        shutil.move(tmp_file, create_file)
        _logger.info("New file added to the assets creation directory: " + create_file)
        return create_file

    async def _write_json(self, json_data, asset_file, metadata_tag):
        json_file = self.asset_helper.get_create_metadata_fullpath(asset_file, metadata_tag)
        # Mode "a" will append if a file with the same name already exists.
        with open(json_file, "a") as f:
            f.write(json.dumps(json_data))
            f.write("\n")
        _logger.info(
            "New metadata added to the assets creation directory: " + json_file
        )
        return json_file
