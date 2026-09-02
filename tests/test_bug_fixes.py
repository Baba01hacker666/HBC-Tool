import io

from hbctool import hasm
from hbctool.hbc import HBC97, HBC98, HBC100
from hbctool.util import BitReader, BitWriter, readint, write


def test_bitcodec_and_readint_64bit_negative():
    raw = b"\x00\x00\x00\x00\x00\x00\x00\x80"
    reader = BitReader(io.BytesIO(raw))
    val = readint(reader, bits=64)
    assert val == -9223372036854775808

    minus_42 = (-42).to_bytes(8, byteorder="little", signed=True)
    reader2 = BitReader(io.BytesIO(minus_42))
    val2 = readint(reader2, bits=64)
    assert val2 == -42


def test_fast_batch_write_buffers():
    buf = io.BytesIO()
    writer = BitWriter(buf)
    data = [1, 2, 3, 4, 255]
    write(writer, data, ["uint", 8, len(data)])
    writer.flush()
    assert buf.getvalue() == bytes([1, 2, 3, 4, 255])


def test_fast_batch_write_exact_count_and_masking():
    # Only serialize n items even if input has more
    buf = io.BytesIO()
    writer = BitWriter(buf)
    write(writer, [1, 2, 3, 4, 5], ["uint", 8, 2])
    writer.flush()
    assert buf.getvalue() == bytes([1, 2])

    # Masking negative / overflowing values
    buf2 = io.BytesIO()
    writer2 = BitWriter(buf2)
    write(writer2, [-1, 256], ["uint", 8, 2])
    writer2.flush()
    assert buf2.getvalue() == bytes([255, 0])


def test_hasm_read_func_preserves_function_name():
    content = """Function<my_custom_function>0(1 params, 2 registers, 0 symbols):
\tRet                  Reg8:0
EndFunction
"""
    func = hasm.read_func([content], 0)
    functionName, paramCount, registerCount, symbolCount, _insts, _ = func
    assert functionName == "my_custom_function"
    assert paramCount == 1
    assert registerCount == 2
    assert symbolCount == 0


def test_hasm_parse_instruction_line_with_tabs_between_operands():
    from hbctool.hasm import _parse_instruction_line

    line = "Mov\tReg8:0,\tReg8:1"
    opcode, operands = _parse_instruction_line(line, 0)
    assert opcode == "Mov"
    assert len(operands) == 2
    assert operands[0] == ("Reg8", False, 0)
    assert operands[1] == ("Reg8", False, 1)


def test_hasm_parse_unnamed_function():
    content = """Function0(0 params, 1 registers, 0 symbols):
\tRet                  Reg8:0
EndFunction
"""
    class _StubHBC:
        def getFunctionCount(self):
            return 1

    parsed = hasm.parse_hasm_functions(content, _StubHBC())
    assert len(parsed) == 1
    assert parsed[0][0] == ""


def test_hbc97_hbc98_hbc100_get_string_id_allocates_new_string():
    for hbc_cls in (HBC97, HBC98, HBC100):
        inst = hbc_cls()
        inst.setObj({
            "header": {
                "functionCount": 0,
                "stringCount": 0,
                "overflowStringCount": 0,
                "stringStorageSize": 0,
                "stringKindCount": 0,
            },
            "stringKinds": [],
            "stringTableEntries": [],
            "stringTableOverflowEntries": [],
            "stringStorage": [],
            "functionHeaders": [],
            "instOffset": 0,
        })
        sid = inst.getStringId("new_dynamic_string")
        assert sid == 0
        val, _ = inst.getString(0)
        assert val == "new_dynamic_string"
        assert inst.getObj()["header"]["stringKindCount"] == 1
        assert len(inst.getObj()["stringKinds"]) == 1

        # Test UTF-16 string allocation
        utf16_str = "🚀 hermes"
        sid_utf16 = inst.getStringId(utf16_str)
        assert sid_utf16 == 1
        entry = inst.getObj()["stringTableEntries"][1]
        assert entry["isUTF16"] == 1
        val_utf16, _ = inst.getString(1)
        assert val_utf16 == utf16_str
