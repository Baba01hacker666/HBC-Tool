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


def test_utf16_le_encoding_matches_unicode_surrogate_pairs():
    from struct import pack

    test_strings = ["Hello World", "React Native 🚀", "Emoji Test 😀🎉🌍", "CJK 𠮷"]
    for s in test_strings:
        c_encoded = s.encode("utf-16-le")

        manual = []
        for char in s:
            cp = ord(char)
            if cp <= 0xFFFF:
                manual.extend(pack("<H", cp))
            else:
                cp -= 0x10000
                high = 0xD800 + (cp >> 10)
                low = 0xDC00 + (cp & 0x3FF)
                manual.extend(pack("<H", high))
                manual.extend(pack("<H", low))

        assert c_encoded == bytes(manual)

