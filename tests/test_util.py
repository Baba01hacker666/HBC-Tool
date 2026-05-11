import pytest
from struct import error as StructError
from hbctool.util import (
    to_uint8, to_uint16, to_uint32,
    to_int8, to_int32, to_double,
    from_uint8, from_uint16, from_uint32,
    from_int8, from_int32, from_double
)

@pytest.mark.parametrize(
    "buf, expected",
    [
        (b"\x00", 0),
        (b"\x01", 1),
        (b"\xff", 255),
        (b"\x01\x02", 1),
    ],
)
def test_to_uint8(buf, expected):
    assert to_uint8(buf) == expected

def test_to_uint8_error():
    with pytest.raises((StructError, IndexError)):
        to_uint8(b"")

@pytest.mark.parametrize(
    "buf, expected",
    [
        (b"\x01\x00", 1),
        (b"\x00\x01", 256),
        (b"\xff\xff", 65535),
        (b"\x01\x02\x03", 513),
    ],
)
def test_to_uint16(buf, expected):
    assert to_uint16(buf) == expected

@pytest.mark.parametrize("buf", [b"\x01", b""])
def test_to_uint16_error(buf):
    with pytest.raises(StructError):
        to_uint16(buf)

@pytest.mark.parametrize(
    "buf, expected",
    [
        (b"\x01\x00\x00\x00", 1),
        (b"\x00\x00\x00\x01", 16777216),
        (b"\xff\xff\xff\xff", 4294967295),
        (b"\x01\x02\x03\x04\x05", 67305985),
    ],
)
def test_to_uint32(buf, expected):
    assert to_uint32(buf) == expected

@pytest.mark.parametrize("buf", [b"\x01\x02\x03", b""])
def test_to_uint32_error(buf):
    with pytest.raises(StructError):
        to_uint32(buf)

@pytest.mark.parametrize(
    "buf, expected",
    [
        (b"\x00", 0),
        (b"\x01", 1),
        (b"\x7f", 127),
        (b"\x80", -128),
        (b"\xff", -1),
        (b"\x01\x02", 1),
    ],
)
def test_to_int8(buf, expected):
    assert to_int8(buf) == expected

def test_to_int8_error():
    with pytest.raises((StructError, IndexError)):
        to_int8(b"")

@pytest.mark.parametrize(
    "buf, expected",
    [
        (b"\x01\x00\x00\x00", 1),
        (b"\xff\xff\xff\xff", -1),
        (b"\x00\x00\x00\x80", -2147483648),
        (b"\xff\xff\xff\x7f", 2147483647),
        (b"\x00\x00\x00\x00", 0),
        (b"\x01\x00\x00\x00\x99", 1),
    ],
)
def test_to_int32(buf, expected):
    assert to_int32(buf) == expected

@pytest.mark.parametrize("buf", [b"\x01\x02\x03", b""])
def test_to_int32_error(buf):
    with pytest.raises(StructError):
        to_int32(buf)

@pytest.mark.parametrize(
    "buf, expected",
    [
        (b"\x00\x00\x00\x00\x00\x00\x00\x00", 0.0),
        (b"\x00\x00\x00\x00\x00\x00\xf0\x3f", 1.0),
        (b"\x00\x00\x00\x00\x00\x00\xf0\xbf", -1.0),
    ],
)
def test_to_double(buf, expected):
    assert to_double(buf) == expected

@pytest.mark.parametrize("buf", [b"\x00" * 7, b""])
def test_to_double_error(buf):
    with pytest.raises(StructError):
        to_double(buf)

def test_from_uint8():
    assert from_uint8(1) == [1]
    assert from_uint8(255) == [255]

def test_from_uint16():
    assert from_uint16(1) == [1, 0]
    assert from_uint16(256) == [0, 1]
    assert from_uint16(65535) == [255, 255]

def test_from_uint32():
    assert from_uint32(1) == [1, 0, 0, 0]
    assert from_uint32(4294967295) == [255, 255, 255, 255]

def test_from_int8():
    assert from_int8(1) == [1]
    assert from_int8(-1) == [255]
    assert from_int8(-128) == [128]

def test_from_int32():
    assert from_int32(1) == [1, 0, 0, 0]
    assert from_int32(-1) == [255, 255, 255, 255]
    assert from_int32(-2147483648) == [0, 0, 0, 128]

def test_from_double():
    assert from_double(1.0) == [0, 0, 0, 0, 0, 0, 240, 63]
    assert from_double(0.0) == [0, 0, 0, 0, 0, 0, 0, 0]
