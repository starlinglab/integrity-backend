from .context import file_util


def test_get_hash_from_filename():
    for filename in [
        "1a2s3d4f5g.jpg",
        "1a2s3d4f5g-meta.json",
        "/a/b/c/1a2s3d4f5g-meta.json",
        "1a2s3d4f5g-foobar.json",
    ]:
        assert file_util.FileUtil.get_hash_from_filename(filename) == "1a2s3d4f5g"
