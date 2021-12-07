from .context import claim

_claim = claim.Claim()


def test_generates_create_claim():
    jwt_payload = {
        "author": {
            "name": "Jane Doe",
            "identifier": "some-identifier",
        },
        "copyright": "copyright holder",
    }
    claim = _claim.generate_create(jwt_payload, {})
    assertions = _claim.assertions_by_label(claim)
    assert claim["vendor"] == "starlinglab"
    assert claim["recorder"] == "Starling Capture"
    assert (
        assertions["stds.schema-org.CreativeWork"]["data"]["author"][0]["name"]
        == "Jane Doe"
    )
    assert assertions["stds.iptc.photo-metadata"]["data"]["dc:creator"] == ["Jane Doe"]
    assert (
        assertions["stds.iptc.photo-metadata"]["data"]["dc:rights"]
        == "copyright holder"
    )


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
