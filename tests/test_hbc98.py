import os
import pytest
import hbctool

BUNDLE_PATH = "/sdcard/analysis/index.android.bundle"

def test_hbc98_load_bundle():
    assert os.path.exists(BUNDLE_PATH), f"Bundle not found: {BUNDLE_PATH}"
    with open(BUNDLE_PATH, "rb") as f:
        hbco = hbctool.hbc.load(f)

    assert hbco.getVersion() == 98
    header = hbco.getHeader()
    assert header["version"] == 98
    assert hbco.getFunctionCount() == 14109
    assert hbco.getStringCount() == 17658

def test_hbc98_disasm_asm_roundtrip(tmp_path):
    assert os.path.exists(BUNDLE_PATH)
    hasm_dir = str(tmp_path / "hasm_out")
    out_bundle = str(tmp_path / "rebuilt.bundle")

    hbctool.disasm(BUNDLE_PATH, hasm_dir)
    assert os.path.exists(os.path.join(hasm_dir, "metadata.json"))
    assert os.path.exists(os.path.join(hasm_dir, "string.json"))
    assert os.path.exists(os.path.join(hasm_dir, "instruction.hasm"))

    hbctool.asm(hasm_dir, out_bundle)
    assert os.path.exists(out_bundle)

    with open(out_bundle, "rb") as f:
        hbco_rebuilt = hbctool.hbc.load(f)

    assert hbco_rebuilt.getVersion() == 98
    assert hbco_rebuilt.getFunctionCount() == 14109
    assert hbco_rebuilt.getStringCount() == 17658
