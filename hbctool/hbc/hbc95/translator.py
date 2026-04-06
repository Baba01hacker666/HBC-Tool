import pathlib
import json
import importlib.util
import os
from hbctool.util import *

basepath = pathlib.Path(__file__).parent.absolute()

_FASTUTIL_SPEC = importlib.util.find_spec("hbctool._fastutil") if os.environ.get("HBCTOOL_FASTUTIL", "0") == "1" else None
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
    "Double": (8, to_double, from_double)
}

with open(f"{basepath}/data/opcode.json", "r") as f:
    opcode_operand = json.load(f)
    opcode_mapper = list(opcode_operand.keys())
    opcode_mapper_inv = {}
    for i, v in enumerate(opcode_mapper):
        opcode_mapper_inv[v] = i


def disassemble(bc):
    if _fastutil is not None:
        return _fastutil.disassemble_ops(bc, opcode_mapper, opcode_operand)

    i = 0
    insts = []
    while i < len(bc):
        opcode = opcode_mapper[bc[i]]
        i += 1
        inst = (opcode, [])
        operand_ts = opcode_operand[opcode]
        for oper_t in operand_ts:
            is_str = oper_t.endswith(":S")
            if is_str:
                oper_t = oper_t[:-2]

            size, conv_to, _ = operand_type[oper_t]
            val = conv_to(bc[i:i + size])
            inst[1].append((oper_t, is_str, val))
            i += size

        insts.append(inst)

    return insts


def assemble(insts):
    if _fastutil is not None:
        return _fastutil.assemble_ops(insts, opcode_mapper_inv)

    bc = []
    for opcode, operands in insts:
        op = opcode_mapper_inv[opcode]
        bc.append(op)
        assert len(opcode_operand[opcode]) == len(operands), f"Malicious instruction: {op}, {operands}"
        for oper_t, _, val in operands:
            assert oper_t in operand_type, f"Malicious operand type: {oper_t}"
            _, _, conv_from = operand_type[oper_t]
            bc += conv_from(val)

    return bc
