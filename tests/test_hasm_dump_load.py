from pathlib import Path
import pytest
from hbctool import hbc, hasm


FIXTURE_BUNDLE = Path("Testfiles/index.android.bundle")


def test_dump_writes_expected_three_files_and_load_roundtrips(tmp_path):
    source = hbc.load(FIXTURE_BUNDLE.open("rb"))

    out_dir = tmp_path / "hasm"
    hasm.dump(source, str(out_dir), force=True)

    assert (out_dir / "metadata.json").is_file()
    assert (out_dir / "string.json").is_file()
    assert (out_dir / "instruction.hasm").is_file()

    rebuilt = hasm.load(str(out_dir))

    assert source.getFunctionCount() == rebuilt.getFunctionCount()
    assert source.getStringCount() == rebuilt.getStringCount()


def test_load_directory_not_exist(tmp_path):
    missing_dir = tmp_path / "missing_dir"
    with pytest.raises(FileNotFoundError, match="does not exist"):
        hasm.load(str(missing_dir))


def test_load_metadata_missing(tmp_path):
    d = tmp_path / "hasm"
    d.mkdir()
    (d / "string.json").touch()
    (d / "instruction.hasm").touch()
    with pytest.raises(FileNotFoundError, match="metadata.json not found"):
        hasm.load(str(d))


def test_load_string_missing(tmp_path):
    d = tmp_path / "hasm"
    d.mkdir()
    (d / "metadata.json").touch()
    (d / "instruction.hasm").touch()
    with pytest.raises(FileNotFoundError, match="string.json not found"):
        hasm.load(str(d))


def test_load_instruction_missing(tmp_path):
    d = tmp_path / "hasm"
    d.mkdir()
    (d / "metadata.json").touch()
    (d / "string.json").touch()
    with pytest.raises(FileNotFoundError, match="instruction.hasm not found"):
        hasm.load(str(d))
