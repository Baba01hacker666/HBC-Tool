import io

import pytest

from hbctool.util import BitReader


def test_readbits_raises_eof_on_empty_stream():
    reader = BitReader(io.BytesIO(b""))

    with pytest.raises(EOFError, match="Unexpected EOF while reading a bit"):
        reader.readbits(1)


def test_readbits_raises_eof_when_stream_exhausted():
    reader = BitReader(io.BytesIO(b"\x80"))

    assert reader.readbits(8) == 0b10000000

    with pytest.raises(EOFError, match="Unexpected EOF while reading a bit"):
        reader.readbits(1)
