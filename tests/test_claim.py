from .context import claim
from .context import config

_claim = claim.Claim()

jwt_payload = {
    "organization_id": "example",
    "author": {
        "type": "Person",
        "identifier": "https://hypha.coop",
        "name": "Benedict Lau",
    },
    "twitter": {
        "type": "Organization",
        "identifier": "https://hypha.coop",
        "name": "HyphaCoop",
    },
    "copyright": "copyright holder",
}

meta = {
    "information": [
        {"name": "Current GPS Latitude", "value": "-15.9321422"},
        {"name": "Current GPS Longitude", "value": "-57.6317174"},
        {"name": "Current GPS Timestamp", "value": "2021-10-30T18:43:14Z"},
        {"name": "Last Known GPS Latitude", "value": "-15.9321422"},
        {"name": "Last Known GPS Longitude", "value": "-57.6317174"},
        {"name": "Last Known GPS Timestamp", "value": "2021-10-30T18:43:14Z"},
        {"name": "Timestamp", "value": "2021-12-17T23:52:47.081Z"},
    ],
    "proof": {
        "hash": "476819d6203a901922683a8a2f5ff32838c58762bf7ef277a823bea4f9edf52c",
        "mimeType": "image/jpeg",
        "timestamp": 1635627729773,
    },
}

signatures = [
    {
        "proofHash": "476819d6203a901922683a8a2f5ff32838c58762bf7ef277a823bea4f9edf52c",
        "provider": "AndroidOpenSSL",
        "signature": "304502205d833310b03e414cc26492dffd17bc10389e3f5631793ef665fffb1ec0ec1cea022100f10cfc74dc6109b348cfc39684c0b53d280058568df54f2c70428d580faff1a4",
        "publicKey": "3059301306072a8648ce3d020106082a8648ce3d03010703420004a28a1e5cd501cf4540a98cb44bf357bcb166678dc3be710c40a405d0de6e7c6f92277ae73b65e08a7a53d465b338a9c751f1f3e0e68cba53e79bb551c0796a83",
    },
    {
        "proofHash": "476819d6203a901922683a8a2f5ff32838c58762bf7ef277a823bea4f9edf52c",
        "provider": "Zion",
        "signature": "304402204e66e42d2551b080b76559131acffe97612a7106d113860697e2fa4a3de8755b022034d83ca1783f4000adf58ebce4f3714c99370511e9c2b334b2fbf0c40b95eafa",
        "publicKey": "Session:\n3059301306072a8648ce3d020106082a8648ce3d03010703420004c33cf16bc6f0a7bac677777c6dfccc2885e76d553fff1799400ab315d6e43062efed4d6c9bc1bd51c8d5d49c16a9b8c8cf7a56cfe12c0c82f05a59d203bb31f9\n\nReceive:\n023a297c1ca2cbb123b2601de7f7a840bd8406e3e96240f8f30c7706bda91264fb\n\nSend:\n023a297c1ca2cbb123b2601de7f7a840bd8406e3e96240f8f30c7706bda91264fb",
    },
]


data = {"meta": meta, "signature": signatures}

fake_address = {
    "city": "Fake Town",
    "state": "Some State",
    "country": "Mock Country",
    "country_code": "br",
}


def test_generates_create_claim(reverse_geocode_mocker):
    reverse_geocode_mocker(fake_address)

    claim = _claim.generate_create(jwt_payload, data)
    assertions = _claim.assertions_by_label(claim)
    assert claim["vendor"] == "starlinglab"
    assert claim["recorder"] == "Starling Capture by Numbers Protocol"

    creative_work = assertions["stds.schema-org.CreativeWork"]
    assert len(creative_work["data"]["author"]) == 2
    author_data = creative_work["data"]["author"][0]
    assert author_data["@type"] == "Person"
    assert author_data["name"] == "Benedict Lau"
    assert author_data["credential"] == []
    assert author_data["identifier"] == "https://hypha.coop"
    twitter_data = creative_work["data"]["author"][1]
    assert twitter_data["@id"] == "https://twitter.com/HyphaCoop"
    assert twitter_data["@type"] == "Organization"
    assert twitter_data["name"] == "HyphaCoop"

    photo_meta_assertion = assertions["stds.iptc.photo-metadata"]
    assert photo_meta_assertion["data"]["dc:creator"] == ["Benedict Lau"]
    assert photo_meta_assertion["data"]["dc:rights"] == "copyright holder"
    assert photo_meta_assertion["data"]["Iptc4xmpExt:LocationCreated"] == {
        "Iptc4xmpExt:CountryCode": "br",
        "Iptc4xmpExt:CountryName": "Mock Country",
        "Iptc4xmpExt:ProvinceState": "Some State",
        "Iptc4xmpExt:City": "Fake Town",
    }

    exif_assertion = assertions["stds.exif"]
    assert exif_assertion["data"]["exif:GPSLatitude"] == "15/1 55/1 6964/125"
    assert exif_assertion["data"]["exif:GPSLatitudeRef"] == "S"
    assert exif_assertion["data"]["exif:GPSLongitude"] == "57/1 37/1 54183/1000"
    assert exif_assertion["data"]["exif:GPSLongitudeRef"] == "W"
    assert exif_assertion["data"]["exif:GPSTimeStamp"] == "2021:10:30 18:43:14 +0000"

    signature_assertion = assertions["org.starlinglab.integrity"]
    signature = signatures[0]
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
    assert authenticated_message["starling:assetHash"] == meta.get("proof").get("hash")
    assert authenticated_message["starling:assetMimeType"] == meta.get("proof").get(
        "mimeType"
    )
    assert (
        authenticated_message["starling:assetCreatedTimestamp"]
        == "2021-12-17T23:52:47.081Z"
    )

    c2pa_actions = assertions["c2pa.actions"]
    assert c2pa_actions["data"]["actions"][0]["when"] == "2021-12-17T23:52:47.081Z"


def test_generates_create_claim_with_missing_author_info(reverse_geocode_mocker):
    reverse_geocode_mocker(fake_address)

    claim = _claim.generate_create({"bad": "jwt"}, data)

    assert claim is not None
    assert claim["vendor"] == "starlinglab"
    assert claim["recorder"] == "Starling Capture by Numbers Protocol"
    assert "stds.schema-org.CreativeWork" not in _claim.assertions_by_label(claim)


def test_generates_create_claim_with_partial_meta(reverse_geocode_mocker):
    reverse_geocode_mocker(fake_address)

    claim = _claim.generate_create(
        jwt_payload,
        {
            "meta": {
                "information": [
                    {
                        "name": "Last Known GPS Timestamp",
                        "value": "2021-10-30T18:43:14Z",
                    }
                ]
            }
        },
    )
    assert claim is not None

    assertions = _claim.assertions_by_label(claim)
    exif_assertion = assertions["stds.exif"]
    assert exif_assertion["data"] == {"exif:GPSTimeStamp": "2021:10:30 18:43:14 +0000"}

    # Should prefer the "Current" timestamp, if one is provided.
    claim = _claim.generate_create(
        jwt_payload,
        {
            "meta": {
                "information": [
                    {
                        "name": "Current GPS Timestamp",
                        "value": "2022-10-30T18:43:14Z",
                    },
                    {
                        "name": "Last Known GPS Timestamp",
                        "value": "2021-10-30T18:43:14Z",
                    },
                ]
            }
        },
    )
    assert claim is not None

    assertions = _claim.assertions_by_label(claim)
    exif_assertion = assertions["stds.exif"]
    assert exif_assertion["data"] == {"exif:GPSTimeStamp": "2022:10:30 18:43:14 +0000"}


def test_generates_create_claim_with_no_reverse_geocode(reverse_geocode_mocker):
    reverse_geocode_mocker(None)

    claim = _claim.generate_create(jwt_payload, data)
    assert claim is not None
    assertions = _claim.assertions_by_label(claim)
    photo_meta_assertion = assertions["stds.iptc.photo-metadata"]
    assert "Iptc4xmpExt:LocationCreated" not in photo_meta_assertion["data"]


def test_generates_create_claim_with_partial_reverse_geocode(reverse_geocode_mocker):
    reverse_geocode_mocker({"city": "Partial Town"})

    claim = _claim.generate_create(jwt_payload, data)
    assert claim is not None
    assertions = _claim.assertions_by_label(claim)
    photo_meta_assertion = assertions["stds.iptc.photo-metadata"]
    assert photo_meta_assertion["data"]["Iptc4xmpExt:LocationCreated"] == {
        "Iptc4xmpExt:City": "Partial Town"
    }


def test_generates_update_claim():
    claim = _claim.generate_update("example")
    assert claim["vendor"] == "starlinglab"


def test_generates_store_claim():
    # Setup some organization-specific configuration
    config.ORGANIZATION_CONFIG.config = {
        "hyphacoop": {
            "creative_work_author": [
                {
                    "@id": "https://twitter.com/example",
                    "@type": "Organization",
                    "identifier": "https://example.com",
                    "name": "example",
                }
            ]
        }
    }

    claim = _claim.generate_store("a-made-up-cid", "example")
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


def test_prefers_current_latlon_with_fallback(reverse_geocode_mocker):
    reverse_geocode_mocker(fake_address)

    claim = _claim.generate_create(
        jwt_payload,
        {
            "meta": {
                "information": [
                    {"name": "Current GPS Latitude", "value": "-1.2"},
                    {"name": "Current GPS Longitude", "value": "-3.4"},
                    {"name": "Last Known GPS Latitude", "value": "-15.9321422"},
                    {"name": "Last Known GPS Longitude", "value": "-57.6317174"},
                ],
            }
        },
    )

    assertions = _claim.assertions_by_label(claim)
    exif_assertion = assertions["stds.exif"]
    assert exif_assertion["data"] == {
        "exif:GPSLatitude": "1/1 11/1 60/1",
        "exif:GPSLatitudeRef": "S",
        "exif:GPSLongitude": "3/1 23/1 60/1",
        "exif:GPSLongitudeRef": "W",
    }

    claim = _claim.generate_create(
        jwt_payload,
        {
            "meta": {
                "information": [
                    {"name": "Last Known GPS Latitude", "value": "-15.9321422"},
                    {"name": "Last Known GPS Longitude", "value": "-57.6317174"},
                ],
            }
        },
    )
    assertions = _claim.assertions_by_label(claim)
    exif_assertion = assertions["stds.exif"]
    assert exif_assertion["data"] == {
        "exif:GPSLatitude": "15/1 55/1 6964/125",
        "exif:GPSLatitudeRef": "S",
        "exif:GPSLongitude": "57/1 37/1 54183/1000",
        "exif:GPSLongitudeRef": "W",
    }
