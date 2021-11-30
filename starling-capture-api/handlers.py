from claim import Claim
from claim_tool import ClaimTool
from multipart import Multipart

from aiohttp import web


async def create(request):
    data = await Multipart().read(request)
    claim = Claim().generate(request["jwt_payload"])
    return_code = ClaimTool().run(claim, data["asset_fullpath"])

    # TODO(anaulin): Add error handling.
    # TODO(anaulin): Add all the required metadata, errors, etc, to response.
    response = {
        "result": "ok",
        "jwt_payload": request["jwt_payload"],
        "claim_tool_code": return_code,
    }
    return web.json_response(response)