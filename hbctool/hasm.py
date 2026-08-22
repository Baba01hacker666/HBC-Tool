import hbctool.hbc as hbcl
import hbctool.compat_json as json
import os
import shutil
import re


class HASMError(ValueError):
    pass


FUNCTION_LINE_RE = re.compile(
    r"^Function<(.*?)>([0-9]+)\(([0-9]+) params, ([0-9]+) registers,\s?([0-9]+) symbols\):$"
)


def write_func(f, func, i, hbc):
    functionName, paramCount, registerCount, symbolCount, insts, _ = func
    f.write(
        f"Function<{functionName}>{i}({paramCount} params, {registerCount} registers, {symbolCount} symbols):\n"
    )
    for opcode, operands in insts:
        f.write(f"\t{opcode.ljust(20, ' ')}\t")
        o = []
        ss = []
        for ii, v in enumerate(operands):
            t, is_str, val = v
            o.append(f"{t}:{val}")

            if is_str:
                if 0 <= val < hbc.getStringCount():
                    try:
                        s, _ = hbc.getString(val)
                        ss.append((ii, val, s))
                    except Exception:
                        ss.append((ii, val, "<invalid string id>"))
                else:
                    ss.append((ii, val, "<invalid string id>"))

        f.write(f"{', '.join(o)}\n")
        if len(ss) > 0:
            for ii, val, s in ss:
                f.write(f"\t; Oper[{ii}]: String({val}) {repr(s)}\n")

            f.write("\n")

    f.write("EndFunction\n\n")


def _write_json_file(path, obj, indent=None):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=indent, ensure_ascii=False)


def ensure_path_removable(path):
    """Refuse output paths that must never be deleted by hbctool."""
    abs_path = os.path.abspath(os.path.normpath(path))
    protected_paths = [
        os.path.abspath(os.sep),
        os.path.abspath(os.path.expanduser("~")),
        os.path.abspath(os.getcwd()),
    ]

    for p in protected_paths:
        try:
            if os.path.commonpath([abs_path, p]) == abs_path:
                raise HASMError(f"Refusing to remove unsafe output directory: {path}")
        except ValueError:
            pass

    if os.path.islink(path):
        raise HASMError(f"Refusing to remove symbolic link: {path}")


def dump(hbc, path, force=False):
    ensure_path_removable(path)

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

    ss = []
    for i in range(stringCount):
        val, header = hbc.getString(i)
        ss.append({"id": i, "isUTF16": header[0] == 1, "value": val})

    _write_json_file(os.path.join(path, "string.json"), ss, indent=4)

    with open(os.path.join(path, "instruction.hasm"), "w", encoding="utf-8") as f:
        for i in range(functionCount):
            write_func(f, hbc.getFunction(i), i, hbc)


def _strip_inline_comment(line):
    """Remove trailing comments while preserving instruction content."""
    return line.split(";", 1)[0].rstrip()


def _parse_instruction_line(line, fid):
    if "	" in line:
        parts = [p for p in line.split("	") if p]
        opcode = parts[0].strip()
        operands_text = parts[1].strip() if len(parts) > 1 else ""
    else:
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
                "function_name": m.group(1),
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


def _functions_equal(current_func, parsed_func):
    """Return True when a HASM function block matches the existing bytecode.

    Loading a dumped project may only change string.json. Re-assembling every
    unchanged function can still perturb bytecode size on bundles that contain
    opcodes/operands the assembler cannot reproduce byte-for-byte. Skip those
    functions so string-only edits preserve the original instruction stream.
    """
    if current_func[:4] != parsed_func[:4]:
        return False

    current_insts = current_func[4]
    parsed_insts = parsed_func[4]
    if len(current_insts) != len(parsed_insts):
        return False

    for (current_opcode, current_operands), (parsed_opcode, parsed_operands) in zip(
        current_insts, parsed_insts
    ):
        if current_opcode != parsed_opcode or len(current_operands) != len(
            parsed_operands
        ):
            return False
        for current_operand, parsed_operand in zip(current_operands, parsed_operands):
            if (
                current_operand[0] != parsed_operand[0]
                or current_operand[2] != parsed_operand[2]
            ):
                return False

    return True


def load(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} does not exist.")
    if not os.path.exists(os.path.join(path, "metadata.json")):
        raise FileNotFoundError("metadata.json not found.")
    if not os.path.exists(os.path.join(path, "string.json")):
        raise FileNotFoundError("string.json not found.")
    if not os.path.exists(os.path.join(path, "instruction.hasm")):
        raise FileNotFoundError("instruction.hasm not found.")

    with open(os.path.join(path, "metadata.json"), "r", encoding="utf-8") as f:
        hbc = hbcl.loado(json.load(f))

    with open(os.path.join(path, "string.json"), "r", encoding="utf-8") as f:
        strings = json.load(f)

    for string in strings:
        current_value, _ = hbc.getString(string["id"])
        if current_value != string["value"]:
            hbc.setString(string["id"], string["value"])

    # Large bundles can reference the same function-name strings tens of thousands
    # of times. Build a reusable lookup once so rebuilding functions stays linear.
    string_id_cache = _build_string_id_cache(hbc)

    offset_shift = 0
    functions_changed = False
    next_fid = 0
    pending = {}
    with open(os.path.join(path, "instruction.hasm"), "r", encoding="utf-8") as f:
        for fid, func in _iter_hasm_functions(f, hbc):
            pending[fid] = func
            while next_fid in pending:
                func = pending.pop(next_fid)
                if _functions_equal(hbc.getFunction(next_fid), func):
                    next_fid += 1
                    continue

                delta = hbc.setFunction(
                    next_fid,
                    func,
                    offset_shift=offset_shift,
                    string_id_cache=string_id_cache,
                )
                functions_changed = True
                offset_shift += delta
                next_fid += 1

    if next_fid != hbc.getFunctionCount():
        raise HASMError("Malformed HASM: missing function blocks.")

    if functions_changed:
        hbc._rebuild_function_offsets()

    return hbc
