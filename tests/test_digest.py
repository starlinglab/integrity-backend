from .context import file_util

fu = file_util.FileUtil()

# https://docs.pytest.org/en/latest/how-to/tmp_path.html


def test_digest(tmp_path):
    unhashed = tmp_path / "unhashed.txt"
    unhashed.write_text("hello world")

    assert (
        fu.digest_sha256(str(unhashed))
        == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    )

    assert fu.digest_md5(str(unhashed)) == "5eb63bbbe01eeed093cb22bb8f5acdc3"
