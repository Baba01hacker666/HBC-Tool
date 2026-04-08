import importlib.util
import json
from pathlib import Path

import pytest


FASTUTIL_AVAILABLE = importlib.util.find_spec("hbctool._fastutil") is not None


@pytest.mark.skipif(not FASTUTIL_AVAILABLE, reason="hbctool._fastutil extension is not built")
def test_fastutil_disasm_then_asm_roundtrip_for_sample_program():
    from hbctool import _fastutil

    opcode_operand = json.loads(Path("hbctool/hbc/hbc96/data/opcode.json").read_text())
    opcode_mapper = list(opcode_operand.keys())
    opcode_mapper_inv = {opcode: i for i, opcode in enumerate(opcode_mapper)}

    insts = [
        ("Unreachable", []),
        ("NewObject", [("Reg8", False, 7)]),
        ("Mov", [("Reg8", False, 7), ("Reg8", False, 5)]),
    ]

    bc = _fastutil.assemble_ops(insts, opcode_mapper_inv, opcode_operand)
    decoded = _fastutil.disassemble_ops(bc, opcode_mapper, opcode_operand)
    assert decoded == insts


@pytest.mark.skipif(not FASTUTIL_AVAILABLE, reason="hbctool._fastutil extension is not built")
def test_fastutil_assemble_rejects_bad_operand_count():
    from hbctool import _fastutil

    opcode_operand = json.loads(Path("hbctool/hbc/hbc96/data/opcode.json").read_text())
    opcode_mapper = list(opcode_operand.keys())
    opcode_mapper_inv = {opcode: i for i, opcode in enumerate(opcode_mapper)}

    bad_insts = [("Mov", [("Reg8", False, 1)])]

    with pytest.raises(ValueError, match="operand length mismatch"):
        _fastutil.assemble_ops(bad_insts, opcode_mapper_inv, opcode_operand)
