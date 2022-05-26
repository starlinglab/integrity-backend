from .asset_helper import AssetHelper
from .log_helper import LogHelper
from . import config

import json
import shutil
import base64
from datetime import datetime, timezone

_logger = LogHelper.getLogger()


global_meta_recorder = None


def get_meta_recorder() -> dict:
    global global_meta_recorder

    if global_meta_recorder is not None:
        return global_meta_recorder

    with open(config.INTEGRITY_RECORDER_ID_JSON, "r") as f:
        global_meta_recorder = json.load(f)

    # Alter to match:
    # https://github.com/starlinglab/integrity-schema/blob/c9248b63f2e6235d4cfe6592c29a171932050110/integrity-backend/input-starling-capture-examples/3e11cc57daf3bad8375935cad4878123acc8d769551ff90f1b1bb0dc597-meta-recorder.json
    # Just add external values dict

    service = next(
        (
            s
            for s in global_meta_recorder["recorderMetadata"]
            if s["service"] == "integrity-backend"
        ),
        None,
    )
    if service is None:
        global_meta_recorder = None
        raise Exception("No recorder metadata found for integrity-backend")

    service["info"].append(
        {
            "type": "external",
            "values": {"name": ""},
        }
    )
    return global_meta_recorder


class Multipart:
    """Handles incoming multi-part requests."""

    def __init__(self, request):
        self.request = request
        self.jwt = self.request.get("jwt_payload")
        self.asset_helper = AssetHelper.from_jwt(self.jwt)

    async def read(self):
        """Reads the multipart section of an incoming request and handles it appropriately.

        Assumes that we will _not_ receive nested multi-parts.

        If it encounters a part with Content-Disposition including name=file, it will store this
        file in our local config.IMAGES_DIR for future processing.

        TODO: read JSON parts into memory and return them

        Args:
            request: an aiohttp request containing multipart data

        Returns:
            Three dictionaries: data, meta_content, meta_recorder
            data is a dict with metadata about the multipart sections encountered
        """

        multipart_data = {}

        # https://github.com/starlinglab/integrity-schema/blob/076fb516b3389cc536e8c21eef2e4df804adb3f5/integrity-backend/input-starling-capture-examples/3e11cc57daf3bad8375935cad4878123acc8d769551ff90f1b1bb0dc597-meta-content.json
        meta_content = {
            "contentMetadata": {
                "name": "Authenticated content",
                "description": "Content captured with Starling Capture application",
                "author": self.jwt.get("author"),
                "extras": {},
                "private": {
                    "providerToken": self.jwt,
                },
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        meta_recorder = get_meta_recorder()
        meta_recorder["timestamp"] = datetime.utcnow().isoformat() + "Z"

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
                multipart_data["meta_raw"] = await part.text()
                multipart_data["meta"] = json.loads(multipart_data["meta_raw"])
                meta_content["contentMetadata"]["mime"] = multipart_data["meta"][
                    "proof"
                ]["mimeType"]
                meta_content["contentMetadata"]["dateCreated"] = (
                    datetime.fromtimestamp(
                        multipart_data["meta"]["proof"]["timestamp"] / 1000,
                        timezone.utc,
                    )
                    .replace(tzinfo=None)
                    .isoformat()
                    + "Z"
                )
                meta_content["contentMetadata"]["private"][
                    "meta"
                ] = base64.standard_b64encode(
                    multipart_data["meta_raw"].encode()
                ).decode()
            elif part.name == "signature":
                multipart_data["signature"] = await part.json()
                meta_content["contentMetadata"]["private"][
                    "signature"
                ] = multipart_data["signature"]
            elif part.name == "caption":
                meta_content["contentMetadata"]["extras"]["caption"] = await part.text()
            elif part.name == "target_provider":
                meta_content["contentMetadata"]["private"][
                    "targetProvider"
                ] = await part.text()
            elif part.name == "tag":
                service = next(
                    (
                        s
                        for s in meta_recorder["recorderMetadata"]
                        if s["service"] == "integrity-backend"
                    ),
                )
                info = next((i for i in service["info"] if i["type"] == "external"))
                info["values"]["name"] = await part.text()
            else:
                _logger.warning("Ignoring multipart part %s", part.name)

        return multipart_data, meta_content, meta_recorder

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
