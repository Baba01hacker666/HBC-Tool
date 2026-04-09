import pytest

from hbctool.hasm import HASMError, parse_hasm_functions


class _StubHBC:
    def __init__(self, function_count):
        self._function_count = function_count

    def getFunctionCount(self):
        return self._function_count


def test_parse_hasm_functions_accepts_inline_comments():
    content = """Function<foo>0(1 params, 2 registers, 0 symbols):
\tLoadConstInt         Reg8:0, UInt32:123 ; inline comment
\tRet                  Reg8:0 ; another comment
EndFunction ; function terminator comment
"""

    parsed = parse_hasm_functions(content, _StubHBC(1))

    assert len(parsed) == 1
    function_name, param_count, register_count, symbol_count, insts, _ = parsed[0]
    assert function_name == "foo"
    assert (param_count, register_count, symbol_count) == (1, 2, 0)
    assert insts == [
        ("LoadConstInt", [("Reg8", False, 0), ("UInt32", False, 123)]),
        ("Ret", [("Reg8", False, 0)]),
    ]


def test_parse_hasm_functions_rejects_bad_operand():
    content = """Function<foo>0(0 params, 1 registers, 0 symbols):
\tRet Reg8:notanint
EndFunction
"""

    with pytest.raises(HASMError, match="Invalid operand value"):
        parse_hasm_functions(content, _StubHBC(1))


def test_parse_hasm_functions_accepts_out_of_order_blocks():
    content = """Function<bar>1(0 params, 1 registers, 0 symbols):
	Ret                  Reg8:0
EndFunction
Function<foo>0(0 params, 1 registers, 0 symbols):
	Ret                  Reg8:0
EndFunction
"""

    parsed = parse_hasm_functions(content, _StubHBC(2))

    assert parsed[0][0] == "foo"
    assert parsed[1][0] == "bar"


def test_parse_hasm_functions_rejects_duplicate_function_blocks():
    content = """Function<foo>0(0 params, 1 registers, 0 symbols):
	Ret                  Reg8:0
EndFunction
Function<foo-again>0(0 params, 1 registers, 0 symbols):
	Ret                  Reg8:0
EndFunction
"""

    with pytest.raises(HASMError, match="Duplicate function block"):
        parse_hasm_functions(content, _StubHBC(1))
