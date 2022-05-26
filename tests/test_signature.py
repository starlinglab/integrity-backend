import json
from .context import signature


def test_verify_androidopenssl_session():
    with open("tests/assets/starling-capture/good/session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/good/session/meta.json", "r") as f:
        meta_raw = f.read()
    assert signature._verify_androidopenssl(meta_raw, signatures[0]) == True


def test_verify_bad_androidopenssl_session():
    with open("tests/assets/starling-capture/bad/session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/bad/session/meta.json", "r") as f:
        meta_raw = f.read()
    assert signature._verify_androidopenssl(meta_raw, signatures[0]) == False


def test_verify_androidopenssl_no_session():
    with open("tests/assets/starling-capture/good/no-session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/good/no-session/meta.json", "r") as f:
        meta_raw = f.read()
    assert signature._verify_androidopenssl(meta_raw, signatures[0]) == True


def test_verify_bad_androidopenssl_no_session():
    with open("tests/assets/starling-capture/bad/no-session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/bad/no-session/meta.json", "r") as f:
        meta_raw = f.read()
    assert signature._verify_androidopenssl(meta_raw, signatures[0]) == False


def test_verify_zion_session():
    with open("tests/assets/starling-capture/good/session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/good/session/meta.json", "r") as f:
        meta_raw = f.read()
    assert signature._verify_zion(meta_raw, signatures[1]) == True


def test_verify_bad_zion_session():
    with open("tests/assets/starling-capture/bad/session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/bad/session/meta.json", "r") as f:
        meta_raw = f.read()
    assert signature._verify_zion(meta_raw, signatures[1]) == False


def test_verify_zion_no_session():
    with open("tests/assets/starling-capture/good/no-session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/good/no-session/meta.json", "r") as f:
        meta_raw = f.read()
    assert signature._verify_zion(meta_raw, signatures[1]) == True


def test_verify_bad_zion_no_session():
    with open("tests/assets/starling-capture/bad/no-session/signature.json", "r") as f:
        signatures = json.load(f)
    with open("tests/assets/starling-capture/bad/no-session/meta.json", "r") as f:
        meta_raw = f.read()
    assert signature._verify_zion(meta_raw, signatures[1]) == False
