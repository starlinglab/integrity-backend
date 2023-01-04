from .context import claim
from .context import config

import json
from copy import deepcopy

_claim = claim.Claim()


fake_address = {
    "city": "Fake Town",
    "state": "Some State",
    "country": "Mock Country",
    "country_code": "br",
}

with open("tests/assets/meta-content.json", "r") as f:
    meta_content = json.load(f)["contentMetadata"]


def test_generate_c2pa_starling_capture():
    claim = _claim.generate_c2pa_starling_capture(meta_content)
    assertions = _claim.assertions_by_label(claim)

    proof = _claim._get_starling_capture_proof(meta_content)

    assert claim["vendor"] == "starlinglab"
    assert claim["recorder"] == "Starling Capture by Numbers Protocol"

    creative_work = assertions["stds.schema-org.CreativeWork"]
    print(creative_work)
    assert len(creative_work["data"]["author"]) == 1
    author_data = creative_work["data"]["author"][0]
    assert author_data["@type"] == "Organization"
    assert author_data["name"] == "Starling Lab"
    assert author_data["credential"] == []
    # assert author_data["identifier"] == "https://hypha.coop"

    photo_meta_assertion = assertions["stds.iptc.photo-metadata"]
    assert photo_meta_assertion["data"]["dc:creator"] == ["Starling Lab"]
    assert photo_meta_assertion["data"]["dc:rights"] == "copyright holder"

    assert photo_meta_assertion["data"]["Iptc4xmpExt:LocationCreated"] == {
        "Iptc4xmpExt:CountryCode": "us",
        "Iptc4xmpExt:CountryName": "United States",
        "Iptc4xmpExt:ProvinceState": "California",
        "Iptc4xmpExt:City": "Stockton",
    }

    exif_assertion = assertions["stds.exif"]
    assert exif_assertion["data"]["exif:GPSLatitude"] == "123,27.36N"
    assert exif_assertion["data"]["exif:GPSLongitude"] == "123,27.36W"
    assert exif_assertion["data"]["exif:GPSTimeStamp"] == "2022-08-15T16:24:20Z"

    signature_assertion = assertions["org.starlinglab.integrity"]
    signature = meta_content["private"]["signatures"][0]
    assert signature_assertion["data"]["starling:identifier"] == signature.get(
        "proofHash"
    )
    first_signature = signature_assertion["data"]["starling:signatures"][0]
    assert first_signature is not None
    assert first_signature["starling:provider"] == signature.get("provider")
    assert first_signature["starling:algorithm"] == "numbers-" + signature.get(
        "provider"
    )
    assert first_signature["starling:publicKey"] == signature.get("publicKey")
    assert first_signature["starling:signature"] == signature.get("signature")
    assert first_signature["starling:authenticatedMessage"] == signature.get(
        "proofHash"
    )
    assert (
        first_signature["starling:authenticatedMessageDescription"]
        == "Internal identifier of the authenticated bundle"
    )
    authenticated_message = first_signature["starling:authenticatedMessagePublic"]
    assert authenticated_message["starling:assetHash"] == proof.get("hash")
    assert authenticated_message["starling:assetMimeType"] == proof.get("mimeType")
    assert (
        authenticated_message["starling:assetCreatedTimestamp"]
        == "2022-04-21T18:27:45.399Z"
    )

    c2pa_actions = assertions["c2pa.actions"]
    assert c2pa_actions["data"]["actions"][0]["when"] == "2022-04-21T18:27:45.399Z"


def test_generate_c2pa_starling_capture_claim_with_missing_author_info():
    this_mc = deepcopy(meta_content)
    del this_mc["author"]
    claim = _claim.generate_c2pa_starling_capture(this_mc)

    assert claim is not None
    assert claim["vendor"] == "starlinglab"
    assert claim["recorder"] == "Starling Capture by Numbers Protocol"
    assert "stds.schema-org.CreativeWork" not in _claim.assertions_by_label(claim)


def test_generate_c2pa_starling_capture_claim_with_partial_meta():
    this_mc = deepcopy(meta_content)
    this_mc["private"]["geolocation"] = {"timestamp": "2022-08-15T16:24:20.305Z"}
    claim = _claim.generate_c2pa_starling_capture(this_mc)
    assert claim is not None

    assertions = _claim.assertions_by_label(claim)
    exif_assertion = assertions["stds.exif"]
    assert exif_assertion["data"] == {
        "exif:GPSVersionID": "2.2.0.0",
        "exif:GPSTimeStamp": "2022-08-15T16:24:20Z",
    }


def test_generate_c2pa_starling_capture_claim_with_no_reverse_geocode():
    this_mc = deepcopy(meta_content)
    # No reverse-geocode
    this_mc["private"]["geolocation"] = {
        "latitude": "123.456",
        "longitude": "-123.456",
        "altitude": "123.456",
        "timestamp": "2022-08-15T16:24:20.305Z",
    }

    claim = _claim.generate_c2pa_starling_capture(this_mc)
    assert claim is not None
    assertions = _claim.assertions_by_label(claim)
    photo_meta_assertion = assertions["stds.iptc.photo-metadata"]
    assert "Iptc4xmpExt:LocationCreated" not in photo_meta_assertion["data"]


def test_generates_update_claim():
    claim = _claim.generate_update({"id": "some-org"}, "some-collection")
    assert claim["vendor"] == "starlinglab"


def test_generates_store_claim():
    # Setup some organization-specific configuration
    config.ORGANIZATION_CONFIG.json_config = {
        "organizations": [
            {
                "id": "example-org",
                "collections": [
                    {
                        "id": "example-collection",
                        "actions": [
                            {
                                "name": "store",
                                "params": {
                                    "creative_work_author": [
                                        {
                                            "@id": "https://twitter.com/example",
                                            "@type": "Organization",
                                            "identifier": "https://example.com",
                                            "name": "example",
                                        }
                                    ]
                                },
                            }
                        ],
                    }
                ],
            }
        ]
    }
    config.ORGANIZATION_CONFIG._index_json_config()

    claim = _claim.generate_store(
        "a-made-up-cid",
        config.ORGANIZATION_CONFIG.get("example-org"),
        "example-collection",
    )
    assertions = _claim.assertions_by_label(claim)
    assert (
        assertions["org.starlinglab.storage.ipfs"]["data"]["starling:provider"]
        == "Web3.Storage"
    )
    assert (
        assertions["org.starlinglab.storage.ipfs"]["data"]["starling:ipfsCID"]
        == "a-made-up-cid"
    )
    assert (
        assertions["org.starlinglab.storage.ipfs"]["data"][
            "starling:assetStoredTimestamp"
        ]
        is not None
    )
    assert assertions["stds.schema-org.CreativeWork"]["data"]["author"] == [
        {
            "@id": "https://twitter.com/example",
            "@type": "Organization",
            "identifier": "https://example.com",
            "name": "example",
        }
    ]
