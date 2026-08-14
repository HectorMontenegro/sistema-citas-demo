import pytest

from appointment_demo.config import ensure_local_demo_url


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:5000/demo",
        "http://localhost:5000/demo/",
        "http://[::1]:5000/demo",
    ],
)
def test_accepts_only_loopback_demo_urls(url):
    assert ensure_local_demo_url(url).endswith("/demo")


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:5000/demo",
        "http://example.com/demo",
        "http://127.0.0.1:5000/another-path",
        "http://user:secret@127.0.0.1:5000/demo",
    ],
)
def test_rejects_non_local_or_ambiguous_urls(url):
    with pytest.raises(ValueError):
        ensure_local_demo_url(url)
