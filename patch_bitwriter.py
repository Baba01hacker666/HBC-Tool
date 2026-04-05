import sys

with open("hbctool/util.py", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.strip() == "self.out.write(bytes((b,)))":
        new_lines.append(line.replace("bytes((b,))", "b.to_bytes(1, 'little')"))
    elif line.strip() == "self.out.write(bytes((self.accumulator,)))":
        new_lines.append(line.replace("bytes((self.accumulator,))", "self.accumulator.to_bytes(1, 'little')"))
    elif line.strip() == "self.out.write(bytes(bs))":
        new_lines.append(line.replace("bytes(bs)", "bytearray(bs)"))
    else:
        new_lines.append(line)

with open("hbctool/util.py", "w") as f:
    f.writelines(new_lines)
