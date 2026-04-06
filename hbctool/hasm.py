from .util import *
import hbctool.hbc as hbcl
import json
import os
import shutil
import re

class HASMError(ValueError):
    pass

FUNCTION_HEADER_RE = re.compile(
    r"^Function<.*?>([0-9]+)\([0-9]+ params, [0-9]+ registers,\s?[0-9]+ symbols\):$",
    re.MULTILINE
)
FUNCTION_BLOCK_RE = re.compile(
    r"Function<.*?>([0-9]+)\(([0-9]+) params, ([0-9]+) registers,\s?([0-9]+) symbols\):\n(.+?)\nEndFunction",
    re.DOTALL
)
FUNCTION_LINE_RE = re.compile(
    r"^Function<(.*?)>([0-9]+)\(([0-9]+) params, ([0-9]+) registers,\s?([0-9]+) symbols\):$"
)


def write_func(f, func, i, hbc):
    functionName, paramCount, registerCount, symbolCount, insts, _ = func
    f.write(f"Function<{functionName}>{i}({paramCount} params, {registerCount} registers, {symbolCount} symbols):\n")
    for opcode, operands in insts:
        f.write(f"\t{opcode.ljust(20,' ')}\t")
        o = []
        ss = []
        for ii, v in enumerate(operands):
            t, is_str, val = v
            o.append(f"{t}:{val}")

            if is_str:
                s, _ = hbc.getString(val)
                ss.append((ii, val, s))
                
        
        f.write(f"{', '.join(o)}\n")
        if len(ss) > 0:
            for ii, val, s in ss:
                f.write(f"\t; Oper[{ii}]: String({val}) {repr(s)}\n")

            f.write("\n")

    f.write("EndFunction\n\n")

def dump(hbc, path, force=False):
    
    if os.path.exists(path) and not force:
        if os.path.abspath(path) in ("/", os.path.expanduser("~")):
            raise HASMError(f"Refusing to remove unsafe output directory: {path}")
        c = input(f"'{path}' exists. Do you want to remove it ? (y/n): ").lower().strip()
        if c[:1] == "y":
            shutil.rmtree(path)
        else:
            exit(1337)
    
    shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path)
    # Write all obj to metadata.json
    f = open(os.path.join(path, "metadata.json"), "w")
    json.dump(hbc.getObj(), f)
    f.close()
    
    stringCount = hbc.getStringCount()
    functionCount = hbc.getFunctionCount()

    ss = []
    for i in range(stringCount):
        val, header = hbc.getString(i)
        ss.append({
            "id": i,
            "isUTF16": header[0] == 1,
            "value": val
        })
    
    f = open(os.path.join(path, "string.json"), "w")
    json.dump(ss, f, indent=4)
    f.close()

    f = open(os.path.join(path, "instruction.hasm"), "w")
    for i in range(functionCount):
        write_func(f, hbc.getFunction(i), i, hbc)
    f.close()

def read_all_func(hasm, hbc):
    functionCount = hbc.getFunctionCount()
    rs = [''] * functionCount

    for m in FUNCTION_HEADER_RE.finditer(hasm):
        fid = int(m.group(1))

        if fid < 0 or fid >= functionCount:
            raise HASMError(f"Invalid function ID {fid}; expected in range [0, {functionCount}).")

        end_pos = hasm.find("\nEndFunction", m.start())
        if end_pos == -1:
            raise HASMError(f"Malformed function block for function {fid}.")

        rs[fid] = hasm[m.start():end_pos + len("\nEndFunction")]

    if any(not func_asm for func_asm in rs):
        raise HASMError("Malformed HASM: missing function blocks.")

    return rs


def read_func(func_asms, i):
    func_asm = func_asms[i]

    m = FUNCTION_BLOCK_RE.search(func_asm)
    if not m:
        raise HASMError(f"Malformed function block for function {i}.")

    functionName = m.group(1)
    paramCount = int(m.group(2))
    registerCount = int(m.group(3))
    symbolCount = int(m.group(4))
    insts_asm = m.group(5)

    inst_lines = insts_asm.split("\n")

    insts = []

    for inst_line in inst_lines:
        inst_line = inst_line.strip()

        if len(inst_line) == 0 or inst_line.startswith(";"):
            continue

        inst_words = inst_line.split()
        if not inst_words:
            continue

        opcode = inst_words[0]

        operands = []
        for oper in inst_words[1:]:
            cleaned = oper.replace(",", "")
            if ":" not in cleaned:
                raise HASMError(f"Malformed operand '{oper}' in function {i}.")
            oper_t, val = cleaned.split(":", 1)
            
            try:
                if oper_t == 'Double':
                    val = float(val)
                else:
                    val = int(val)
            except ValueError as exc:
                raise HASMError(f"Invalid operand value '{val}' ({oper_t}) in function {i}.") from exc
            
            operands.append((oper_t, False, val))
        
        insts.append((opcode, operands))
    
    return functionName, paramCount, registerCount, symbolCount, insts, None



def parse_hasm_functions(hasm_content, hbc):
    function_count = hbc.getFunctionCount()
    results = [None] * function_count

    lines = hasm_content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        m = FUNCTION_LINE_RE.match(line)
        if not m:
            i += 1
            continue

        function_name = m.group(1)
        fid = int(m.group(2))
        param_count = int(m.group(3))
        register_count = int(m.group(4))
        symbol_count = int(m.group(5))

        if fid < 0 or fid >= function_count:
            raise HASMError(f"Invalid function ID {fid}; expected in range [0, {function_count}).")

        i += 1
        insts = []
        while i < len(lines):
            cur = lines[i].strip()
            if cur == "EndFunction":
                break

            if not cur or cur.startswith(";"):
                i += 1
                continue

            if "\t" in cur:
                parts = [p for p in cur.split("\t") if p]
                opcode = parts[0].strip()
                operands_text = parts[1].strip() if len(parts) > 1 else ""
            else:
                sp = cur.split(None, 1)
                opcode = sp[0]
                operands_text = sp[1] if len(sp) > 1 else ""

            operands = []
            if operands_text:
                for oper in operands_text.split(","):
                    item = oper.strip()
                    if not item:
                        continue
                    if ":" not in item:
                        raise HASMError(f"Malformed operand '{item}' in function {fid}.")
                    oper_t, val = item.split(":", 1)
                    try:
                        parsed_val = float(val) if oper_t == "Double" else int(val)
                    except ValueError as exc:
                        raise HASMError(f"Invalid operand value '{val}' ({oper_t}) in function {fid}.") from exc
                    operands.append((oper_t, False, parsed_val))

            insts.append((opcode, operands))
            i += 1

        if i >= len(lines) or lines[i].strip() != "EndFunction":
            raise HASMError(f"Malformed function block for function {fid}.")

        results[fid] = (function_name, param_count, register_count, symbol_count, insts, None)
        i += 1

    if any(v is None for v in results):
        raise HASMError("Malformed HASM: missing function blocks.")

    return results


def load(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} does not exist.")
    if not os.path.exists(os.path.join(path, "metadata.json")):
        raise FileNotFoundError("metadata.json not found.")
    if not os.path.exists(os.path.join(path, "string.json")):
        raise FileNotFoundError("string.json not found.")
    if not os.path.exists(os.path.join(path, "instruction.hasm")):
        raise FileNotFoundError("instruction.hasm not found.")

    f = open(os.path.join(path, "metadata.json"), "r")
    hbc = hbcl.loado(json.load(f))
    f.close()

    f = open(os.path.join(path, "instruction.hasm"), "r")
    hasm_content = f.read()
    f.close()

    f = open(os.path.join(path, "string.json"), "r")
    strings = json.load(f)
    f.close()

    for string in strings:
        hbc.setString(string["id"], string["value"])
  
    funcs = parse_hasm_functions(hasm_content, hbc)
    offset_shift = 0
    for i, func in enumerate(funcs):
        delta = hbc.setFunction(i, func, offset_shift=offset_shift)
        offset_shift += delta

    hbc._rebuild_function_offsets()

        
    return hbc
