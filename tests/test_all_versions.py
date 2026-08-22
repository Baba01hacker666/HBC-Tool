import os
import hbctool

HBC96_BUNDLE = "Testfiles/index.android.bundle"

def test_hbc96_disasm_asm_roundtrip(tmp_path):
    assert os.path.exists(HBC96_BUNDLE), f"Bundle not found: {HBC96_BUNDLE}"
    hasm_dir = str(tmp_path / "hasm_96")
    out_bundle = str(tmp_path / "rebuilt_96.bundle")

    hbctool.disasm(HBC96_BUNDLE, hasm_dir)
    assert os.path.exists(os.path.join(hasm_dir, "metadata.json"))
    assert os.path.exists(os.path.join(hasm_dir, "instruction.hasm"))

    hbctool.asm(hasm_dir, out_bundle)
    assert os.path.exists(out_bundle)

    with open(out_bundle, "rb") as f:
        hbco = hbctool.hbc.load(f)

    assert hbco.getVersion() == 96
    assert hbco.getFunctionCount() == 38420

def test_all_hbc_versions_registered():
    from hbctool.hbc import _HBC_MODULES, HBC, HBC96, HBC97, HBC98, HBC100
    for ver in (96, 97, 98, 100):
        assert ver in _HBC_MODULES

    assert HBC[96] is HBC96
    assert HBC[97] is HBC97
    assert HBC[98] is HBC98
    assert HBC[100] is HBC100
