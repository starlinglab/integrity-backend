import config

import os
import logging

_logger = logging.getLogger(__name__)


class Multipart:
    # Implementation assumes there won't be nested multi-parts.
    async def read(self, request):
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
                # TODO: write file to disc
            else:
                # TODO: Add processing of other parts
                _logger.info("Ignoring multipart part %s", part.name)
        return multipart_data

    async def _write_file(self, part):
        local_filename = os.path.join(config.IMAGES_DIR, part.filename)
        # Mode "x" will throw an error if a file with that name already exists.
        with open(local_filename, "xb") as f:
            while True:
                chunk = await part.read_chunk()
                if not chunk:
                    break
                f.write(chunk)
        return local_filename
