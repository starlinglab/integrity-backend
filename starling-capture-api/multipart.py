import config

import os
import logging

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
            a dictionary with metadata about the multipart sections encountered
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
                multipart_data["image_filename"] = await self._write_file(part)
            else:
                # TODO: Add processing of other parts
                _logger.info("Ignoring (for now) multipart part %s", part.name)
        return multipart_data

    async def _write_file(self, part):
        local_filename = os.path.join(config.IMAGES_DIR, part.filename)
        # Mode "x" will throw an error if a file with the same name already exists.
        with open(local_filename, "xb") as f:
            while True:
                chunk = await part.read_chunk()
                if not chunk:
                    # No more chunks, done reading this part.
                    break
                f.write(chunk)
        return local_filename
