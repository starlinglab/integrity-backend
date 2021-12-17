from .context import claim

_claim = claim.Claim()

jwt_payload = {
    "author": {
        "name": "Jane Doe",
        "identifier": "some-identifier",
    },
    "copyright": "copyright holder",
}

meta = {
    "information": [
        {"name": "Last Known GPS Latitude", "value": "-15.9321422"},
        {"name": "Last Known GPS Longitude", "value": "-57.6317174"},
        {"name": "Last Known GPS Timestamp", "value": "2021-10-30T18:43:14Z"},
    ]
}

fake_address = {
    "city": "Fake Town",
    "state": "Some State",
    "country": "Mock Country",
    "country_code": "br",
}


def test_generates_create_claim(reverse_geocode_mocker):
    reverse_geocode_mocker(fake_address)

    claim = _claim.generate_create(jwt_payload, meta)
    assertions = _claim.assertions_by_label(claim)
    assert claim["vendor"] == "starlinglab"
    assert claim["recorder"] == "Starling Capture by Numbers Protocol"
    assert (
        assertions["stds.schema-org.CreativeWork"]["data"]["author"][0]["name"]
        == "Jane Doe"
    )
    photo_meta_assertion = assertions["stds.iptc.photo-metadata"]
    assert photo_meta_assertion["data"]["dc:creator"] == ["Jane Doe"]
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


def test_generates_create_claim_with_missing_author_info(reverse_geocode_mocker):
    reverse_geocode_mocker(fake_address)

    claim = _claim.generate_create({"bad": "jwt"}, meta)

    assert claim is not None
    assert claim["vendor"] == "starlinglab"
    assert claim["recorder"] == "Starling Capture by Numbers Protocol"
    assert "stds.schema-org.CreativeWork" not in _claim.assertions_by_label(claim)


def test_generates_create_claim_with_partial_meta(reverse_geocode_mocker):
    reverse_geocode_mocker(fake_address)

    claim = _claim.generate_create(
        jwt_payload,
        {
            "information": [
                {"name": "Last Known GPS Timestamp", "value": "2021-10-30T18:43:14Z"}
            ]
        },
    )
    assert claim is not None

    assertions = _claim.assertions_by_label(claim)
    exif_assertion = assertions["stds.exif"]
    assert exif_assertion["data"] == {"exif:GPSTimeStamp": "2021:10:30 18:43:14 +0000"}


def test_generates_create_claim_with_no_reverse_geocode(reverse_geocode_mocker):
    reverse_geocode_mocker(None)

    claim = _claim.generate_create(jwt_payload, meta)
    assert claim is not None
    assertions = _claim.assertions_by_label(claim)
    photo_meta_assertion = assertions["stds.iptc.photo-metadata"]
    assert "Iptc4xmpExt:LocationCreated" not in photo_meta_assertion["data"]


def test_generates_create_claim_with_partial_reverse_geocode(reverse_geocode_mocker):
    reverse_geocode_mocker({"city": "Partial Town"})

    claim = _claim.generate_create(jwt_payload, meta)
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
