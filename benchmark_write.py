import time
from hbctool.util import BitReader, read, BitWriter, write

class ByteIO:
    def __init__(self, v=b""):
        self.buf = v
        self.pos = 0

    def write(self, b):
        self.buf += b

    def read(self, n=-1):
        if n==-1:
            o = self.buf[self.pos:]
            self.pos = len(self.buf)
            return o

        o = self.buf[self.pos:self.pos+n]
        self.pos += len(o)
        return o

io = ByteIO()
fw = BitWriter(io)
st = time.time()
for i in range(100000):
    write(fw, i, ["uint", 32, 1])
    write(fw, [i, i+1], ["uint", 16, 2])
    write(fw, i & 15, ["bit", 4, 1])
    write(fw, i & 15, ["bit", 4, 1])
print("write time:", time.time() - st)
