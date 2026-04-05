import time
from hbctool.util import BitReader, read, BitWriter, write

class ByteIO_orig:
    def __init__(self, v=b""):
        self.buf = v
        self.pos = 0

    def write(self, b):
        self.buf += b

class ByteIO_bytearray:
    def __init__(self, v=b""):
        self.buf = bytearray(v)
        self.pos = 0

    def write(self, b):
        self.buf.extend(b)

io = ByteIO_orig()
st = time.time()
for i in range(100000):
    io.write(b"A")
print("bytes time:", time.time() - st)

io = ByteIO_bytearray()
st = time.time()
for i in range(100000):
    io.write(b"A")
print("bytearray time:", time.time() - st)
