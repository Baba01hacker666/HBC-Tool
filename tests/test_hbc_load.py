import io
import pytest

from hbctool import hbc


def test_load_plain_js_bundle_raises_actionable_error():
    fake_bundle = io.BytesIO(b"var __BUNDLE_START_TIME__ = this.nativePerformanceNow()")

    with pytest.raises(ValueError, match="plain JavaScript Metro bundle"):
        hbc.load(fake_bundle)


def test_public_hbc_mapping_still_resolves_version_classes():
    hbc96 = hbc.HBC[96]
    assert hbc96.__name__ == "HBC96"


def test_public_hbc_version_symbols_remain_available():
    from hbctool.hbc import HBC96

    assert HBC96 is hbc.HBC[96]
