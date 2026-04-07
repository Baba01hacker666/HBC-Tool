import io
import pytest
from hbctool.util import BitReader

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
