from .context import iscn


def test_register_success(requests_mock):
    registration = {"foo": 123, "bar": "other stuff"}
    requests_mock.post(iscn._REGISTER, status_code=200)
    assert iscn.Iscn.register(registration)
    assert len(requests_mock.request_history) == 1
    assert requests_mock.last_request.json() == {"metadata": registration}


def test_register_failure(requests_mock):
    requests_mock.post(iscn._REGISTER, status_code=500)
    assert not iscn.Iscn.register({})
