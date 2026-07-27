import os
import pytest
import hbctool

HBC96_BUNDLE = "Testfiles/index.android.bundle"
HBC98_BUNDLE = "/sdcard/analysis/index.android.bundle"

def test_hbc96_disasm_asm_roundtrip(tmp_path):
    assert os.path.exists(HBC96_BUNDLE)
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

def test_hbc98_disasm_asm_roundtrip(tmp_path):
    assert os.path.exists(HBC98_BUNDLE)
    hasm_dir = str(tmp_path / "hasm_98")
    out_bundle = str(tmp_path / "rebuilt_98.bundle")

    hbctool.disasm(HBC98_BUNDLE, hasm_dir)
    assert os.path.exists(os.path.join(hasm_dir, "metadata.json"))
    assert os.path.exists(os.path.join(hasm_dir, "instruction.hasm"))

    hbctool.asm(hasm_dir, out_bundle)
    assert os.path.exists(out_bundle)

    with open(out_bundle, "rb") as f:
        hbco = hbctool.hbc.load(f)

    assert hbco.getVersion() == 98
    assert hbco.getFunctionCount() == 14109

def test_hbc97_and_hbc100_supported_versions():
    from hbctool.hbc import _HBC_MODULES
    assert 96 in _HBC_MODULES
    assert 97 in _HBC_MODULES
    assert 98 in _HBC_MODULES
    assert 100 in _HBC_MODULES
