import pytest
from struct import error as StructError
from hbctool.util import to_uint16

@pytest.mark.parametrize("buf, expected", [
    (b"\x01\x00", 1),
    (b"\x00\x01", 256),
    (b"\xff\xff", 65535),
    (b"\x01\x02\x03", 513), # Should only use the first 2 bytes (0x0201)
])
def test_to_uint16_happy_path(buf, expected):
    assert to_uint16(buf) == expected

@pytest.mark.parametrize("buf", [
    b"\x01",    # Too small (1 byte)
    b"",        # Empty
])
def test_to_uint16_error_cases(buf):
    with pytest.raises(StructError):
        to_uint16(buf)
