import json
import os
import re
import shutil

import hbctool.hbc as hbcl

from .util import *  # noqa: F403


class HASMError(ValueError):
    pass


FUNCTION_HEADER_RE = re.compile(
    r"^Function(?:<(.*?)>)?([0-9]+)\([0-9]+ params, [0-9]+ registers,\s?[0-9]+ symbols\):$",
    re.MULTILINE,
)
FUNCTION_BLOCK_RE = re.compile(
    r"Function(?:<(.*?)>)?([0-9]+)\(([0-9]+) params, ([0-9]+) registers,\s?([0-9]+) symbols\):\n(.+?)\nEndFunction",
    re.DOTALL,
)
FUNCTION_LINE_RE = re.compile(
    r"^Function(?:<(.*?)>)?([0-9]+)\(([0-9]+) params, ([0-9]+) registers,\s?([0-9]+) symbols\):$"
)


def write_func(f, func, i, hbc, strings_cache=None):
    functionName, paramCount, registerCount, symbolCount, insts, _ = func
    lines = [
        f"Function<{functionName}>{i}({paramCount} params, {registerCount} registers, {symbolCount} symbols):\n"
    ]
    str_count = hbc.getStringCount()
    for opcode, operands in insts:
        o = []
        ss = []
        for ii, v in enumerate(operands):
            t, is_str, val = v
            o.append(f"{t}:{val}")

            if is_str:
                if 0 <= val < str_count:
                    try:
                        s = (
                            strings_cache[val]
                            if strings_cache is not None
                            else hbc.getString(val)[0]
                        )
                        ss.append((ii, val, s))
                    except (UnicodeDecodeError, IndexError, ValueError):
                        ss.append((ii, val, "<invalid string id>"))
                else:
                    ss.append((ii, val, "<invalid string id>"))

        lines.append(f"\t{opcode.ljust(20,' ')}\t{', '.join(o)}\n")
        if len(ss) > 0:
            for ii, val, s in ss:
                lines.append(f"\t; Oper[{ii}]: String({val}) {s!r}\n")
            lines.append("\n")

    lines.append("EndFunction\n\n")
    f.writelines(lines)


def _write_json_file(path, obj, indent=None):
    with open(path, "w") as f:
        json.dump(obj, f, indent=indent)


def dump(hbc, path, force=False):
    abs_path = os.path.abspath(os.path.normpath(path))
    if abs_path in ("/", os.path.expanduser("~"), os.getcwd()):
        raise HASMError(f"Refusing to remove unsafe output directory: {path}")

    if os.path.islink(path):
        raise HASMError(f"Refusing to remove symbolic link: {path}")

    if os.path.exists(path):
        if not force:
            raise FileExistsError(f"Output directory already exists: {path}")

        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        else:
            os.remove(path)

    os.makedirs(path)
    # Write all obj to metadata.json
    _write_json_file(os.path.join(path, "metadata.json"), hbc.getObj())

    stringCount = hbc.getStringCount()
    functionCount = hbc.getFunctionCount()

    strings_cache = []
    ss = []
    for i in range(stringCount):
        val, header = hbc.getString(i)
        ss.append({"id": i, "isUTF16": header[0] == 1, "value": val})
        strings_cache.append(val)

    _write_json_file(os.path.join(path, "string.json"), ss, indent=4)

    with open(os.path.join(path, "instruction.hasm"), "w") as f:
        for i in range(functionCount):
            write_func(f, hbc.getFunction(i), i, hbc, strings_cache=strings_cache)


def read_all_func(hasm, hbc):
    functionCount = hbc.getFunctionCount()
    rs = [""] * functionCount

    for m in FUNCTION_HEADER_RE.finditer(hasm):
        fid = int(m.group(2))

        if fid < 0 or fid >= functionCount:
            raise HASMError(
                f"Invalid function ID {fid}; expected in range [0, {functionCount})."
            )

        end_pos = hasm.find("\nEndFunction", m.start())
        if end_pos == -1:
            raise HASMError(f"Malformed function block for function {fid}.")

        rs[fid] = hasm[m.start() : end_pos + len("\nEndFunction")]

    if any(not func_asm for func_asm in rs):
        raise HASMError("Malformed HASM: missing function blocks.")

    return rs


def read_func(func_asms, i):
    func_asm = func_asms[i]

    m = FUNCTION_BLOCK_RE.search(func_asm)
    if not m:
        raise HASMError(f"Malformed function block for function {i}.")

    functionName = m.group(1) or ""
    paramCount = int(m.group(3))
    registerCount = int(m.group(4))
    symbolCount = int(m.group(5))
    insts_asm = m.group(6)

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
                if oper_t == "Double":
                    val = float(val)
                else:
                    val = int(val)
            except ValueError as exc:
                raise HASMError(
                    f"Invalid operand value '{val}' ({oper_t}) in function {i}."
                ) from exc

            operands.append((oper_t, False, val))

        insts.append((opcode, operands))

    return functionName, paramCount, registerCount, symbolCount, insts, None


def _strip_inline_comment(line):
    """Remove trailing comments while preserving instruction content."""
    return line.split(";", 1)[0].rstrip()


def _parse_instruction_line(line, fid):
    sp = line.split(None, 1)
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
                raise HASMError(
                    f"Invalid operand value '{val}' ({oper_t}) in function {fid}."
                ) from exc
            operands.append((oper_t, False, parsed_val))

    return opcode, operands


def _iter_hasm_functions(lines, hbc):
    function_count = hbc.getFunctionCount()
    seen = [False] * function_count
    current = None

    for raw_line in lines:
        line = _strip_inline_comment(raw_line.strip())

        if current is None:
            if not line:
                continue

            m = FUNCTION_LINE_RE.match(line)
            if not m:
                continue

            fid = int(m.group(2))
            if fid < 0 or fid >= function_count:
                raise HASMError(
                    f"Invalid function ID {fid}; expected in range [0, {function_count})."
                )
            if seen[fid]:
                raise HASMError(f"Duplicate function block for function {fid}.")

            current = {
                "fid": fid,
                "function_name": m.group(1) or "",
                "param_count": int(m.group(3)),
                "register_count": int(m.group(4)),
                "symbol_count": int(m.group(5)),
                "insts": [],
            }
            continue

        if line == "EndFunction":
            fid = current["fid"]
            seen[fid] = True
            yield (
                fid,
                (
                    current["function_name"],
                    current["param_count"],
                    current["register_count"],
                    current["symbol_count"],
                    current["insts"],
                    None,
                ),
            )
            current = None
            continue

        if not line or line.startswith(";"):
            continue

        current["insts"].append(_parse_instruction_line(line, current["fid"]))

    if current is not None:
        raise HASMError(f"Malformed function block for function {current['fid']}.")

    if any(not parsed for parsed in seen):
        raise HASMError("Malformed HASM: missing function blocks.")


def parse_hasm_functions(hasm_content, hbc):
    function_count = hbc.getFunctionCount()
    results = [None] * function_count

    for fid, func in _iter_hasm_functions(hasm_content.splitlines(), hbc):
        results[fid] = func

    return results


def _build_string_id_cache(hbc):
    string_id_cache = {}
    for sid in range(hbc.getStringCount()):
        value, _ = hbc.getString(sid)
        string_id_cache.setdefault(value, sid)
    return string_id_cache


def load(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} does not exist.")
    if not os.path.exists(os.path.join(path, "metadata.json")):
        raise FileNotFoundError("metadata.json not found.")
    if not os.path.exists(os.path.join(path, "string.json")):
        raise FileNotFoundError("string.json not found.")
    if not os.path.exists(os.path.join(path, "instruction.hasm")):
        raise FileNotFoundError("instruction.hasm not found.")

    with open(os.path.join(path, "metadata.json"), "r") as f:
        hbc = hbcl.loado(json.load(f))

    with open(os.path.join(path, "string.json"), "r") as f:
        strings = json.load(f)

    string_id_cache = {}
    for string in strings:
        sid = string["id"]
        sval = string["value"]
        current_value, _ = hbc.getString(sid)
        if current_value != sval:
            hbc.setString(sid, sval)
        string_id_cache.setdefault(sval, sid)

    offset_shift = 0
    next_fid = 0
    pending = {}
    with open(os.path.join(path, "instruction.hasm"), "r") as f:
        for fid, func in _iter_hasm_functions(f, hbc):
            pending[fid] = func
            while next_fid in pending:
                delta = hbc.setFunction(
                    next_fid,
                    pending.pop(next_fid),
                    offset_shift=offset_shift,
                    string_id_cache=string_id_cache,
                )
                offset_shift += delta
                next_fid += 1

    if next_fid != hbc.getFunctionCount():
        raise HASMError("Malformed HASM: missing function blocks.")

    hbc._rebuild_function_offsets()

    return hbc
