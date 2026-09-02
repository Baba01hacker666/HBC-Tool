import io
import pytest

from hbctool.util import BitReader


# ---- Existing EOF Tests ----

def test_readbits_raises_eof_on_empty_stream():
    reader = BitReader(io.BytesIO(b""))

    with pytest.raises(EOFError, match="Unexpected EOF while reading a bit"):
        reader.readbits(1)


def test_readbits_raises_eof_when_stream_exhausted():
    reader = BitReader(io.BytesIO(b"\x80"))

    assert reader.readbits(8) == 0b10000000

    with pytest.raises(EOFError, match="Unexpected EOF while reading a bit"):
        reader.readbits(1)


# ---- Existing readall Tests ----

def test_readall_empty_stream():
    reader = BitReader(io.BytesIO(b""))
    assert reader.readall() == []


def test_readall_full_stream():
    reader = BitReader(io.BytesIO(b"\x01\x02\x03\xff\x00"))
    assert reader.readall() == [1, 2, 3, 255, 0]


def test_readall_partial_stream():
    reader = BitReader(io.BytesIO(b"\x01\x02\x03\xff\x00"))
    assert reader.readbytes(2) == 258
    assert reader.readall() == [3, 255, 0]


def test_readall_multiple_times():
    reader = BitReader(io.BytesIO(b"\x01\x02\x03"))
    assert reader.readall() == [1, 2, 3]
    assert reader.readall() == []

# ---- New Tests ----

def test_init_modes():
    # File-like with read, seek, tell
    f1 = io.BytesIO(b"test1")
    r1 = BitReader(f1)
    assert r1.read_raw(5) == b"test1"

    # File-like with read only
    class ReadOnly:
        def read(self, n=-1):
            return b"test2"
    r2 = BitReader(ReadOnly())
    assert r2.read_raw(5) == b"test2"

    # Not file-like
    r3 = BitReader(None)
    with pytest.raises(EOFError):
        r3.read_raw(1)

def test_context_manager():
    with BitReader(io.BytesIO(b"test")) as r:
        assert isinstance(r, BitReader)
        assert r.read_raw(4) == b"test"

def test_read_raw():
    r = BitReader(io.BytesIO(b"\x01\x02\x03\x04"))
    assert r.read_raw(2) == b"\x01\x02"
    assert r.read_raw(1) == b"\x03"

    # Out of bounds
    with pytest.raises(EOFError, match="Unexpected EOF while reading 2 bytes."):
        r.read_raw(2)

def test_read_raw_bcount_error():
    r = BitReader(io.BytesIO(b"\xaa\x55"))
    r.readbits(1) # Leaves unaligned bits
    with pytest.raises(RuntimeError):
        r.read_raw(1)

def test_readbits_basic():
    # 0b10101010
    r = BitReader(io.BytesIO(b"\xaa"))
    assert r.readbits(1) == 1
    assert r.readbits(1) == 0
    assert r.readbits(2) == 2 # 10
    assert r.readbits(4) == 10 # 1010

def test_readbits_across_bytes():
    # 0b11001100 0b10101010
    r = BitReader(io.BytesIO(b"\xcc\xaa"))
    assert r.readbits(4) == 12 # 1100
    assert r.readbits(6) == 50 # 110010 (remaining 4 from first byte, 2 from second byte)
    assert r.readbits(6) == 42 # 101010


def test_readbytes():
    r = BitReader(io.BytesIO(b"\x01\x02\x03\x04"))
    assert r.readbytes(1) == 1
    assert r.readbytes(2) == 0x0203
    assert r.readbytes(1) == 4

def test_readbyte():
    r = BitReader(io.BytesIO(b"\x05\x06"))
    assert r._readbyte() == 5
    assert r._readbyte() == 6
    with pytest.raises(EOFError):
        r._readbyte()

def test_readbyte_bcount_error():
    r = BitReader(io.BytesIO(b"\xaa"))
    r.readbits(1)
    with pytest.raises(RuntimeError):
        r._readbyte()

def test_seek_and_tell():
    r = BitReader(io.BytesIO(b"\xaa\xbb\xcc"))
    assert r.tell() == 0
    r.read_raw(2)
    assert r.tell() == 2
    r.seek(0)
    assert r.tell() == 0
    assert r.read_raw(1) == b"\xaa"

    # Seek should clear bit state
    r.readbits(1)
    # This readbits reads 1 bit, 7 bits remain
    r.seek(1)
    # The bit state should be cleared, we can do a raw read now
    assert r.read_raw(1) == b"\xbb"

def test_pad():
    r = BitReader(io.BytesIO(b"\x01\x02\x03\x04\x05\x06\x07\x08"))

    # Initial alignment is 0 (0 % 4 == 0)
    r.pad(4)
    assert r.tell() == 0

    r.read_raw(1)
    assert r.tell() == 1
    r.pad(4)
    assert r.tell() == 4

    r.read_raw(2)
    assert r.tell() == 6
    r.pad(8)
    assert r.tell() == 8

def test_pad_invalid_alignment():
    r = BitReader(io.BytesIO(b"\x01"))
    with pytest.raises(ValueError, match="Support alignment as many as 8 bytes."):
        r.pad(0)
    with pytest.raises(ValueError, match="Support alignment as many as 8 bytes."):
        r.pad(3)
    with pytest.raises(ValueError, match="Support alignment as many as 8 bytes."):
        r.pad(9)


def test_readbits_remained():
    r = BitReader(io.BytesIO(b"\xaa")) # 10101010

    # 0b10101010
    v = r.readbits(4, remained=True)
    assert v == 10 # 1010

    # The accumulator is shifted, remaining bits are 1010
    v = r.readbits(4)
    assert v == 10 # 1010
