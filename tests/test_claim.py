from .context import claim

_claim = claim.Claim()

jwt_payload = {
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
        {"name": "Last Known GPS Latitude", "value": "-15.9321422"},
        {"name": "Last Known GPS Longitude", "value": "-57.6317174"},
        {"name": "Last Known GPS Timestamp", "value": "2021-10-30T18:43:14Z"},
        {"name": "Timestamp", "value": "2021-12-17T23:52:47.081Z"},
    ],
    "proof": {
        "hash": "109213b0e49d5eba0ebd679a9e87d33eebd8dc47255ae5043022f512052f0f9b",
        "mimeType": "image/jpeg",
        "timestamp": 1635627729773,
    },
}

signature = {
    "proofHash": "109213b0e49d5eba0ebd679a9e87d33eebd8dc47255ae5043022f512052f0f9b",
    "provider": "AndroidOpenSSL",
    "signature": "304502200e57c4795f3a674b334332089a50ecf02dad72d5b9297db55bf67e3454f79289022100a927f5cfb7728c9b9650102f076f956918953dc3cbd0ab51f6dc1bbf7a6dceb5",
    "publicKey": "3059301306072a8648ce3d020106082a8648ce3d0301070342000463760bc21e0f0d2fa4186c67f06e866fa075fc50a28fa9330299ac9f3b31af87ffa06aca9749085a6da162b1b685a4deeba93fecfae94c7706d55e370384cb91",
}


data = {"meta": meta, "signature": signature}

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
    assert (
        exif_assertion["data"]["exif:GPSLatitude"]
        == "15/1 55/1 3920383475626017/70368744177664"
    )
    assert exif_assertion["data"]["exif:GPSLatitudeRef"] == "S"
    assert (
        exif_assertion["data"]["exif:GPSLongitude"]
        == "57/1 37/1 7625579331556737/140737488355328"
    )
    assert exif_assertion["data"]["exif:GPSLongitudeRef"] == "W"
    assert exif_assertion["data"]["exif:GPSTimeStamp"] == "2021:10:30 18:43:14 +0000"

    signature_assertion = assertions["org.starlinglab.integrity"]
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
    claim = _claim.generate_update()
    assert claim["vendor"] == "starlinglab"


def test_generates_store_claim():
    claim = _claim.generate_store("a-made-up-cid")
    assertions = _claim.assertions_by_label(claim)
    assert (
        assertions["org.starlinglab.storage.ipfs"]["data"]["starling:IpfsCid"]
        == "a-made-up-cid"
    )
