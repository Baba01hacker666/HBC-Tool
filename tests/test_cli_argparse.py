import pytest

import hbctool


def test_main_disasm_defaults(monkeypatch):
    called = {}

    def fake_disasm(hbc_file, hasm_path):
        called["hbc_file"] = hbc_file
        called["hasm_path"] = hasm_path

    monkeypatch.setattr(hbctool, "disasm", fake_disasm)
    hbctool.main(["disasm", "bundle.hbc"])

    assert called == {"hbc_file": "bundle.hbc", "hasm_path": hbctool.DEFAULT_HASM_PATH}


def test_main_asm_defaults(monkeypatch):
    called = {}

    def fake_asm(hasm_path, hbc_file):
        called["hasm_path"] = hasm_path
        called["hbc_file"] = hbc_file

    monkeypatch.setattr(hbctool, "asm", fake_asm)
    hbctool.main(["asm"])

    assert called == {
        "hasm_path": hbctool.DEFAULT_HASM_PATH,
        "hbc_file": hbctool.DEFAULT_HBC_FILE,
    }


def test_main_aliases(monkeypatch):
    called = {"disasm": False, "asm": False}

    monkeypatch.setattr(hbctool, "disasm", lambda *_: called.__setitem__("disasm", True))
    monkeypatch.setattr(hbctool, "asm", lambda *_: called.__setitem__("asm", True))

    hbctool.main(["d", "bundle.hbc"])
    hbctool.main(["a"])

    assert called == {"disasm": True, "asm": True}


def test_main_domain_errors_exit(monkeypatch):
    monkeypatch.setattr(hbctool, "disasm", lambda *_: (_ for _ in ()).throw(FileNotFoundError("missing")))

    with pytest.raises(SystemExit) as exc:
        hbctool.main(["disasm", "missing.hbc"])

    assert exc.value.code == 1
