import sys

with open("hbctool/util.py", "r") as f:
    text = f.read()

text = text.replace("""    def _writebit(self, bit, remaining=-1):
        if remaining > -1:
            self.accumulator |= bit << (remaining - 1)
        else:
            self.accumulator |= bit << (7 - self.bcount + self.remained)

        self.bcount += 1

        if self.bcount == 8:
            self.flush()""", """    def _writebit(self, bit, remaining=-1):
        if remaining > -1:
            self.accumulator |= bit << (remaining - 1)
        else:
            self.accumulator |= bit << (7 - self.bcount + self.remained)

        self.bcount += 1

        if self.bcount == 8:
            self.out.write(self.accumulator.to_bytes(1, 'little'))
            self.accumulator = 0
            self.bcount = 0
            self.remained = 0
            self.write += 1""")

with open("hbctool/util.py", "w") as f:
    f.write(text)
