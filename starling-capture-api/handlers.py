from claim_tool import ClaimTool

from aiohttp import web


async def process_image(request):
    # TODO(anaulin): Pass in image from request, instead of hardcoded image.
    return_code = ClaimTool().run(_generate_claim(request), "image.jpg")

    # TODO(anaulin): Add error handling.
    response = {
        "result": "ok",
        "jwt_payload": request["jwt_payload"],
        "claim_tool_code": return_code,
    }
    return web.json_response(response)


def _generate_claim(request):
    # TODO(anaulin): Generate the claim based on request data
    return {
        "vendor": "Starling",
        "recorder": "Starling Capture Api",
        "assertions": [
            {
                "label": "starling.assertion",
                "data": {"jwt_payload": request["jwt_payload"]},
            }
        ],
    }
