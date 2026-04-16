from hbctool.util import memcpy

def test_memcpy_list_happy_path():
    dest = [0, 0, 0, 0, 0]
    src = [1, 2, 3]
    memcpy(dest, src, 1, 3)
    assert dest == [0, 1, 2, 3, 0]

def test_memcpy_list_full_copy():
    dest = [0, 0, 0]
    src = [1, 2, 3]
    memcpy(dest, src, 0, 3)
    assert dest == [1, 2, 3]

def test_memcpy_bytes_src():
    dest = [0, 0, 0, 0, 0]
    src = b"\x01\x02\x03"
    memcpy(dest, src, 1, 3)
    assert dest == [0, 1, 2, 3, 0]

def test_memcpy_bytearray_src():
    dest = [0, 0, 0, 0, 0]
    src = bytearray([1, 2, 3])
    memcpy(dest, src, 1, 3)
    assert dest == [0, 1, 2, 3, 0]

def test_memcpy_zero_length():
    dest = [0, 0, 0]
    src = [1, 2, 3]
    memcpy(dest, src, 1, 0)
    assert dest == [0, 0, 0]
