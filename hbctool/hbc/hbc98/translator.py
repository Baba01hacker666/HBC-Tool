import pathlib
import json
import importlib.util
import os
from hbctool.util import *

basepath = pathlib.Path(__file__).parent.absolute()

_FASTUTIL_SPEC = (
    importlib.util.find_spec("hbctool._fastutil")
    if os.environ.get("HBCTOOL_FASTUTIL", "0") == "1"
    else None
)
if _FASTUTIL_SPEC is not None:
    from hbctool import _fastutil
else:
    _fastutil = None


operand_type = {
    "Reg8": (1, to_uint8, from_uint8),
    "Reg32": (4, to_uint32, from_uint32),
    "UInt8": (1, to_uint8, from_uint8),
    "UInt16": (2, to_uint16, from_uint16),
    "UInt32": (4, to_uint32, from_uint32),
    "Addr8": (1, to_int8, from_int8),
    "Addr32": (4, to_int32, from_int32),
    "Imm32": (4, to_int32, from_int32),
    "Double": (8, to_double, from_double),
}

with open(basepath / "data" / "opcode.json", "r") as f:
    opcode_operand = json.load(f)
    opcode_mapper = list(opcode_operand.keys())
    opcode_mapper_inv = {}
    for i, v in enumerate(opcode_mapper):
        opcode_mapper_inv[v] = i


def disassemble(bc):
    if _fastutil is not None:
        try:
            return _fastutil.disassemble_ops(bc, opcode_mapper, opcode_operand)
        except Exception:
            pass

    i = 0
    insts = []
    bc_len = len(bc)
    while i < bc_len:
        op_byte = bc[i]
        if op_byte >= len(opcode_mapper):
            insts.append(("UnparsedByte", [("UInt8", False, op_byte)]))
            i += 1
            continue

        opcode = opcode_mapper[op_byte]
        operand_ts = opcode_operand[opcode]

        req_size = 0
        for oper_t in operand_ts:
            if oper_t.endswith(":S"):
                oper_t = oper_t[:-2]
            req_size += operand_type[oper_t][0]

        if i + 1 + req_size > bc_len:
            insts.append(("UnparsedByte", [("UInt8", False, op_byte)]))
            i += 1
            continue

        i += 1
        inst = (opcode, [])
        for oper_t in operand_ts:
            is_str = oper_t.endswith(":S")
            if is_str:
                oper_t = oper_t[:-2]

            size, conv_to, _ = operand_type[oper_t]
            val = conv_to(bc[i : i + size])
            inst[1].append((oper_t, is_str, val))
            i += size

        insts.append(inst)

    return insts


def assemble(insts):
    if _fastutil is not None:
        try:
            return _fastutil.assemble_ops(insts, opcode_mapper_inv, opcode_operand)
        except Exception:
            pass

    bc = []
    for opcode, operands in insts:
        if opcode == "UnparsedByte":
            bc.append(operands[0][2])
            continue

        op = opcode_mapper_inv[opcode]
        bc.append(op)
        assert len(opcode_operand[opcode]) == len(
            operands
        ), f"Malicious instruction: {op}, {operands}"
        for oper_t, _, val in operands:
            assert oper_t in operand_type, f"Malicious operand type: {oper_t}"
            _, _, conv_from = operand_type[oper_t]
            bc.extend(conv_from(val))

    return bc
