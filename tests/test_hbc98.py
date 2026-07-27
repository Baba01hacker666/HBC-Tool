import os
import pytest
import hbctool
from hbctool.hbc import HBC, HBC98

def test_hbc98_version_registration():
    assert 98 in hbctool.hbc._HBC_MODULES
    assert HBC[98] is HBC98
    hbc_instance = HBC98()
    assert hbc_instance.getVersion() == 98

def test_hbc98_structure_and_opcode_loading():
    hbc_instance = HBC98()
    assert hbc_instance.getVersion() == 98
    from hbctool.hbc.hbc98.translator import opcode_mapper, opcode_operand
    assert len(opcode_mapper) > 0
    assert "DeclareGlobalVar" in opcode_operand
    assert "GetById" in opcode_operand
