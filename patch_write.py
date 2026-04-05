import sys

with open("hbctool/util.py", "r") as f:
    lines = f.readlines()

new_lines = []
in_write = False
for i, line in enumerate(lines):
    if line.startswith("def write("):
        in_write = True
        new_lines.append(line)
        new_lines.append("""    t = format[0]
    bits = format[1]
    n = format[2]

    if t == "uint":
        if n == 1:
            writeuint(f, v if not isinstance(v, list) else v[0], bits=bits)
        else:
            if not isinstance(v, list): v = [v]
            for i in range(n): writeuint(f, v[i], bits=bits)
    elif t == "int":
        if n == 1:
            writeint(f, v if not isinstance(v, list) else v[0], bits=bits)
        else:
            if not isinstance(v, list): v = [v]
            for i in range(n): writeint(f, v[i], bits=bits)
    elif t == "bit":
        if n == 1:
            writebits(f, v if not isinstance(v, list) else v[0], bits=bits)
        else:
            if not isinstance(v, list): v = [v]
            for i in range(n): writebits(f, v[i], bits=bits)
    else:
        raise Exception(f"Data type {t} is not supported.")
""")
    elif in_write and not line.startswith(" ") and not line.startswith("\t") and len(line.strip()) > 0:
        in_write = False
        new_lines.append(line)
    elif not in_write:
        new_lines.append(line)

with open("hbctool/util.py", "w") as f:
    f.writelines(new_lines)
