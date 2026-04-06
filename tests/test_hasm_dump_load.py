from pathlib import Path

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
