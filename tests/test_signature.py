import json
from .context import signature


def test_verify_androidopenssl():
    with open("tests/assets/starling-capture-test/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture-test/meta.json", "r") as f:
        meta_raw = f.read()
    assert signature._verify_androidopenssl(meta_raw, signatures[0]) == True


def test_verify_zion():
    with open("tests/assets/starling-capture-test/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture-test/meta.json", "r") as f:
        meta_raw = f.read()
    assert signature._verify_zion(meta_raw, signatures[1]) == True
