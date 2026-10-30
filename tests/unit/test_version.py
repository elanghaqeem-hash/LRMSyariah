import pytest

from lrm_engine.common.version import EngineBuild


@pytest.mark.unit
def test_engine_identity():
    build = EngineBuild("1.2.3", "a" * 40)
    assert build.identity == "1.2.3+git." + "a" * 40
    assert EngineBuild("1.2.3+build", "a" * 40).identity == "1.2.3+build.git." + "a" * 40


@pytest.mark.unit
@pytest.mark.parametrize("semver", ["1", "v1.2.3", "1.02.3", "1.2", ""])
def test_invalid_semver(semver):
    with pytest.raises(ValueError):
        EngineBuild(semver, "a" * 40)


@pytest.mark.unit
@pytest.mark.parametrize("sha", ["", "a" * 7, "A" * 40, "g" * 40])
def test_invalid_git_sha(sha):
    with pytest.raises(ValueError):
        EngineBuild("1.2.3", sha)
