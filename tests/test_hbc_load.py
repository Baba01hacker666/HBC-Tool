import io
import pytest

from hbctool import hbc


def test_load_plain_js_bundle_raises_actionable_error():
    fake_bundle = io.BytesIO(b"var __BUNDLE_START_TIME__ = this.nativePerformanceNow()")

    with pytest.raises(ValueError, match="plain JavaScript Metro bundle"):
        hbc.load(fake_bundle)
