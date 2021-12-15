from .asset_helper import AssetHelper

import logging
import shutil

_asset_helper = AssetHelper()
_logger = logging.getLogger(__name__)


class Multipart:
    """Handles incoming multi-part requests."""

    # Implementation assumes there won't be nested multi-parts.
    async def read(self, request):
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
        reader = await request.multipart()
        part = None
        while True:
            part = await reader.next()
            if part is None:
                # No more parts, we're done reading.
                break
            if part.name == "file":
                multipart_data["asset_fullpath"] = await self._write_file(part, request.path)
            elif part.name == "meta":
                multipart_data["meta"] = await part.json()
            else:
                _logger.warning("Ignoring multipart part %s", part.name)
        return multipart_data

    async def _write_file(self, part, request_path):
        # Write file in temporary directory.
        tmp_file = _asset_helper.get_tmp_file_fullpath(".jpg")

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
            create_file = _asset_helper.get_create_proofmode_file_fullpath(tmp_file)
        else:
            create_file = _asset_helper.get_create_file_fullpath(tmp_file)
        shutil.move(tmp_file, create_file)
        _logger.info("New file added to the assets creation directory: " + create_file)

        return create_file
