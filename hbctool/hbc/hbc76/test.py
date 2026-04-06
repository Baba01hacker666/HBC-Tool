from hbctool import hbc as hbcl, hasm
from .translator import assemble, disassemble
import unittest
import re
import pathlib
import json

basepath = pathlib.Path(__file__).parent.absolute()
repo_root = basepath.parents[2]


def _fixture(*parts, required=True):
    candidate_paths = [
        basepath.joinpath("example", *parts),
        repo_root.joinpath("Testfiles", *parts),
    ]
    for path in candidate_paths:
        if path.exists():
            return path
    if required:
        raise unittest.SkipTest(f"Missing required fixture: {'/'.join(parts)}")
    return None

class TestHBC76(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestHBC76, self).__init__(*args, **kwargs)
        self.hbc = hbcl.load(open(_fixture("index.android.bundle"), "rb"))
        objdump_fixture = _fixture("objdump.out", required=False)
        pretty_fixture = _fixture("pretty.out", required=False)
        raw_fixture = _fixture("raw.out", required=False)
        self.objdump = open(objdump_fixture, "r").read() if objdump_fixture else None
        self.pretty = open(pretty_fixture, "r").read() if pretty_fixture else None
        self.raw = open(raw_fixture, "r").read() if raw_fixture else None

    def test_get_function(self):
        if self.objdump is None or self.pretty is None:
            self.skipTest("Missing objdump.out/pretty.out fixtures")
        target_offsets = re.findall(r"([0-9a-f]+) \<_[0-9]+\>", self.objdump)
        target_args = re.findall(r"Function<(.*?)>([0-9]+)\(([0-9]+) params, ([0-9]+) registers,\s?([0-9]+) symbols\):", self.pretty)
        functionCount = self.hbc.getFunctionCount()

        self.assertEqual(functionCount, len(target_offsets))
        self.assertEqual(functionCount, len(target_args))

        for i in range(functionCount):
            target_offset = target_offsets[i]
            target_functionName, _, target_paramCount, target_registerCount, target_symbolCount = target_args[i]
            try:
                functionName, paramCount, registerCount, symbolCount, _, funcHeader = self.hbc.getFunction(i)
            except AssertionError:
                self.fail()

            self.assertEqual(functionName, target_functionName)
            self.assertEqual(paramCount, int(target_paramCount))
            self.assertEqual(registerCount, int(target_registerCount))
            self.assertEqual(symbolCount, int(target_symbolCount))
            self.assertEqual(funcHeader["offset"], int(target_offset, 16))
    
    def test_get_string(self):
        if self.pretty is None:
            self.skipTest("Missing pretty.out fixture")
        target_strings = re.findall(r"[is][0-9]+\[([UTFASCI16-]+), ([0-9]+)..([0-9-]+)\].*?:\s?(.*)", self.pretty)
        stringCount = self.hbc.getStringCount()

        self.assertEqual(stringCount, len(target_strings))

        for i in range(stringCount):
            val, header = self.hbc.getString(i)
            isUTF16, offset, length = header

            t, target_start, target_end, target_val = target_strings[i]

            target_isUTF16 = t == "UTF-16"
            target_offset = int(target_start)
            target_length = int(target_end) - target_offset + 1

            self.assertEqual(isUTF16, target_isUTF16)
            self.assertEqual(offset, target_offset)
            self.assertEqual(length, target_length)
            self.assertEqual(val, target_val)

    def test_translator(self):
        functionCount = self.hbc.getFunctionCount()

        for i in range(functionCount):
            _, _, _, _, bc, _ = self.hbc.getFunction(i, disasm=False)

            self.assertEqual(assemble(disassemble(bc)), bc)
class TestParser76(unittest.TestCase):
    def test_hbc(self):
        f = open(_fixture("index.android.bundle"), "rb")
        hbc = hbcl.load(f)
        f.close()
        f = open("/tmp/hbctool_test.android.bundle", "wb")
        hbcl.dump(hbc, f)
        f.close()

        f = open(_fixture("index.android.bundle"), "rb")
        a = f.read()
        f.close()
        f = open("/tmp/hbctool_test.android.bundle", "rb")
        b = f.read()
        f.close()

        self.assertEqual(a, b)

    def test_hasm(self):
        f = open(_fixture("index.android.bundle"), "rb")
        a = hbcl.load(f)
        f.close()
        hasm.dump(a, "/tmp/hbctool_test", force=True)
        b = hasm.load("/tmp/hbctool_test")

        self.assertEqual(json.dumps(a.getObj()), json.dumps(b.getObj()))
