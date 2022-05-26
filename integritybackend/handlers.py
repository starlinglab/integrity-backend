import os
import zipfile
from contextlib import contextmanager

from .log_helper import LogHelper
from .multipart import Multipart
from .asset_helper import AssetHelper
from .file_util import FileUtil
from . import signature

from aiohttp import web

import traceback


_logger = LogHelper.getLogger()

_file_util = FileUtil()


def create_inputBundle(httppost, jwt, config_preproc):
    # parse JWT -
    # verify content sigs
    # store a compliant zip into input folder
    pass


async def create(request):
    with error_handling_and_response() as response:
        jwt = request["jwt_payload"]
        if not jwt.get("collection_id") or not jwt.get("organization_id"):
            raise ValueError("JWT is missing collection or organization ID")

        # Extract data from post and create metadata files
        data, meta_content, meta_recorder = await Multipart(request).read()

        if "meta" not in data:
            raise ValueError("Missing 'meta' section in request")

        # Actions().c2pa_starling_capture(data.get("asset_fullpath"), request.get("jwt_payload"), data)

        asset_path = data["asset_fullpath"]

        # Verify the data
        if not signature.verify_create_hashes(asset_path, data):
            raise Exception("Hashes did not match actual asset hash")
        if not signature.verify_all(data["meta_raw"], data["signature"]):
            raise Exception("Not all signatures verified")

        asset_helper = AssetHelper.from_jwt(jwt)
        tmp_zip_path = asset_helper.get_tmp_file_fullpath(".zip")
        asset_hash = _file_util.digest_sha256(asset_path)

        # Create zip
        with zipfile.ZipFile(tmp_zip_path, "w") as zipf:
            zipf.writestr(f"{asset_hash}-meta-content.json", meta_content)
            zipf.writestr(f"{asset_hash}-meta-recorder.json", meta_recorder)
            zipf.write(asset_hash + os.path.splitext(asset_path)[1])

        # Move zip to input dir, named as the hash of itself
        os.rename(
            tmp_zip_path,
            os.path.join(
                asset_helper.path_for_input(jwt["collection_id"]),
                _file_util.digest_sha256(tmp_zip_path),
            )
            + ".zip",
        )

    return web.json_response(response, status=response.get("status_code"))


@contextmanager
def error_handling_and_response():
    """Context manager to wrap the core of a handler implementation with error handlers.

    Yields:
        response: dict containing a status and any errors encountered
    """
    response = {"status": "ok", "status_code": 200}
    try:
        yield response
    except Exception as err:
        print(traceback.format_exc())
        _logger.error(err)
        response["error"] = f"{err}"
        response["status"] = "error"
        if type(err) == ValueError:
            response["status_code"] = 400
        else:
            response["status_code"] = 500
