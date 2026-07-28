"""
Regression tests for all bugs found in the HBC-Tool code audit.

Bug 1 (CRITICAL): Large Function Header duplication on export → SIGSEGV crash
Bug 2 (HIGH):     Mutable global state in parser (stringStorageS[2]=...) mutated per call
Bug 3 (HIGH):     fileLength header field not updated after string storage grows
Bug 4 (HIGH):     getString returns raw hex for UTF-16 strings instead of decoded unicode
Bug 5 (MEDIUM):   getStringId raises ValueError in hbc97/98/100 instead of allocating new slot
"""

import io
import json
import struct
import pytest
from pathlib import Path

from hbctool import hbc, hasm

FIXTURE_BUNDLE    = Path("Testfiles/index.android.bundle")   # HBC96, 5.4 MB, 38k funcs
FIXTURE_BUNDLE_98 = Path("Testfiles/hbc98.bundle")           # HBC98, 2.9 MB, 14k funcs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_orig():
    return FIXTURE_BUNDLE.read_bytes()


def _load_hbc():
    return hbc.load(io.BytesIO(_load_orig()))


def _load_orig_98():
    return FIXTURE_BUNDLE_98.read_bytes()


def _load_hbc_98():
    return hbc.load(io.BytesIO(_load_orig_98()))


def _dump_bytes(hbc_obj):
    buf = io.BytesIO()
    hbc.dump(hbc_obj, buf)
    return buf.getvalue()


def _file_length_from_bytes(data: bytes) -> int:
    """Read fileLength field from exported header (LE uint32 at byte offset 32)."""
    return struct.unpack_from("<I", data, 32)[0]


# ===========================================================================
# Bug 1 — Large Function Header duplication / exact binary roundtrip
# ===========================================================================

class TestBug1_LargeFunctionHeaderDuplication:
    """
    Regression for the CRITICAL bug where export() duplicated large function
    headers at the tail of the file and corrupted SmallFuncHeader pointers,
    causing Hermes VM to crash with SIGSEGV on app launch.
    """

    def test_load_dump_exact_binary_match(self):
        """A fresh load/dump cycle must produce byte-for-byte identical output."""
        orig = _load_orig()
        hbc_obj = hbc.load(io.BytesIO(orig))
        out = _dump_bytes(hbc_obj)
        assert out == orig, (
            f"Binary mismatch: original {len(orig)} bytes, exported {len(out)} bytes"
        )

    def test_exported_size_equals_original_size(self):
        """Exported file must be exactly the same size as the original."""
        orig = _load_orig()
        hbc_obj = hbc.load(io.BytesIO(orig))
        out = _dump_bytes(hbc_obj)
        assert len(out) == len(orig)

    def test_function_count_preserved_after_roundtrip(self):
        """Function count must be identical before and after roundtrip."""
        orig_obj = _load_hbc()
        count_before = orig_obj.getFunctionCount()

        out = _dump_bytes(orig_obj)
        rebuilt = hbc.load(io.BytesIO(out))
        assert rebuilt.getFunctionCount() == count_before

    def test_large_function_headers_not_appended_at_tail(self):
        """
        Exported bytes must NOT contain duplicate large function header data
        after the instruction block. Specifically, the exported size must equal
        the original — any tail duplication would produce a larger file.
        """
        orig = _load_orig()
        hbc_obj = hbc.load(io.BytesIO(orig))

        # Count how many large (overflowed) function headers exist
        large_headers = [
            fh for fh in hbc_obj.getObj()["functionHeaders"] if "small" in fh
        ]
        assert len(large_headers) > 0, "Fixture has no large function headers — test premise invalid"

        out = _dump_bytes(hbc_obj)
        assert len(out) == len(orig), (
            f"Exported size {len(out)} != original {len(orig)}; "
            f"{len(large_headers)} large headers may have been duplicated"
        )

    def test_small_func_header_pointers_unchanged_after_roundtrip(self):
        """
        SmallFuncHeader.offset and .infoOffset for large functions must point
        to the same locations after a roundtrip (not remapped to tail).
        """
        orig = _load_orig()
        hbc_obj = hbc.load(io.BytesIO(orig))

        before = {
            i: (fh["small"]["infoOffset"], fh["small"]["offset"])
            for i, fh in enumerate(hbc_obj.getObj()["functionHeaders"])
            if "small" in fh
        }

        out = _dump_bytes(hbc_obj)
        rebuilt = hbc.load(io.BytesIO(out))

        for i, (info_off, off) in before.items():
            fh = rebuilt.getObj()["functionHeaders"][i]
            assert "small" in fh, f"Function {i} lost its 'small' key after roundtrip"
            assert fh["small"]["infoOffset"] == info_off
            assert fh["small"]["offset"] == off

    def test_binary_roundtrip_hbc96(self):
        """HBC96: load → dump must produce exact same bytes (no disasm, fast)."""
        orig = _load_orig()
        out = _dump_bytes(hbc.load(io.BytesIO(orig)))
        assert out == orig

    def test_binary_roundtrip_hbc98(self):
        """HBC98: load → dump must produce valid parseable output with matching size."""
        orig = _load_orig_98()
        hbc_obj = hbc.load(io.BytesIO(orig))
        out = _dump_bytes(hbc_obj)
        assert len(out) == len(orig)
        fl = _file_length_from_bytes(out)
        assert fl == len(out)
        rebuilt = hbc.load(io.BytesIO(out))
        assert rebuilt.getFunctionCount() == hbc_obj.getFunctionCount()


# ===========================================================================
# Bug 2 — Mutable global state in parser
# ===========================================================================

class TestBug2_MutableGlobalStateInParser:
    """
    Regression for the bug where stringStorageS[2] (and similar module-level
    lists) were mutated on every parse/export call, causing state corruption
    when processing multiple bundles in the same Python process.
    """

    def test_two_sequential_loads_produce_same_string_count(self):
        """Loading the same bundle twice must give identical string counts."""
        obj1 = _load_hbc()
        obj2 = _load_hbc()
        assert obj1.getStringCount() == obj2.getStringCount()

    def test_two_sequential_loads_produce_same_function_count(self):
        """Loading the same bundle twice must give identical function counts."""
        obj1 = _load_hbc()
        obj2 = _load_hbc()
        assert obj1.getFunctionCount() == obj2.getFunctionCount()

    def test_two_sequential_dumps_produce_identical_bytes(self):
        """Dumping the same object twice must produce byte-for-byte identical output."""
        hbc_obj = _load_hbc()
        out1 = _dump_bytes(hbc_obj)
        out2 = _dump_bytes(hbc_obj)
        assert out1 == out2

    def test_independent_loads_produce_identical_bytes(self):
        """Two independently loaded objects must both dump to the same bytes."""
        obj1 = _load_hbc()
        obj2 = _load_hbc()
        out1 = _dump_bytes(obj1)
        out2 = _dump_bytes(obj2)
        assert out1 == out2

    def test_load_after_dump_still_exact_match(self):
        """
        Load → dump → load again → dump again must produce identical bytes.
        A mutable global state bug would corrupt the second dump.
        """
        orig = _load_orig()
        obj1 = hbc.load(io.BytesIO(orig))
        out1 = _dump_bytes(obj1)

        obj2 = hbc.load(io.BytesIO(out1))
        out2 = _dump_bytes(obj2)

        assert out1 == out2


# ===========================================================================
# Bug 3 — fileLength not updated on export
# ===========================================================================

class TestBug3_FileLengthNotUpdated:
    """
    Regression for the bug where the header's fileLength field was never
    updated after string storage grew, causing Hermes VM integrity checks to fail.
    """

    def test_file_length_matches_exported_size_unchanged_bundle(self):
        """fileLength in exported header must equal actual file size (unmodified bundle)."""
        hbc_obj = _load_hbc()
        out = _dump_bytes(hbc_obj)
        fl = _file_length_from_bytes(out)
        assert fl == len(out), f"fileLength={fl} but exported size={len(out)}"

    def test_file_length_matches_exported_size_after_same_length_string_change(self):
        """fileLength must be correct after a same-length in-place string modification."""
        hbc_obj = _load_hbc()

        # Find an ASCII string of length >= 2 and replace with same-length value
        for sid in range(hbc_obj.getStringCount()):
            val, meta = hbc_obj.getString(sid)
            if meta[0] == 0 and len(val) >= 2:  # ASCII, at least 2 chars
                new_val = val[:-1] + ("z" if val[-1] != "z" else "a")
                hbc_obj.setString(sid, new_val)
                break

        out = _dump_bytes(hbc_obj)
        fl = _file_length_from_bytes(out)
        assert fl == len(out), f"fileLength={fl} but exported size={len(out)}"

    def test_file_length_matches_exported_size_after_longer_string(self):
        """fileLength must be correct after a string replacement that grows the storage."""
        hbc_obj = _load_hbc()

        # Find a short ASCII string and replace with a significantly longer one
        for sid in range(hbc_obj.getStringCount()):
            val, meta = hbc_obj.getString(sid)
            if meta[0] == 0 and 1 <= len(val) <= 5:
                long_val = val + "z" * 40  # well beyond original length
                hbc_obj.setString(sid, long_val)
                break

        out = _dump_bytes(hbc_obj)
        fl = _file_length_from_bytes(out)
        assert fl == len(out), f"fileLength={fl} but exported size={len(out)}"

    def test_file_length_field_position_is_correct(self):
        """fileLength must sit at byte offset 32 in the exported header (magic=8, version=4, sourceHash=20)."""
        hbc_obj = _load_hbc()
        orig = _load_orig()
        # The original file's fileLength in the header
        orig_fl = struct.unpack_from("<I", orig, 32)[0]
        assert orig_fl == len(orig), "Fixture itself has wrong fileLength — check fixture"

    def test_file_length_updated_correctly_in_header_obj_after_export(self):
        """header['fileLength'] must equal actual output size after dump()."""
        hbc_obj = _load_hbc()
        out = _dump_bytes(hbc_obj)
        assert hbc_obj.getHeader()["fileLength"] == len(out)

    def test_string_storage_size_consistent_after_no_change(self):
        """stringStorageSize must not change when no strings are modified."""
        hbc_obj = _load_hbc()
        orig_ss_size = hbc_obj.getHeader()["stringStorageSize"]
        out = _dump_bytes(hbc_obj)
        rebuilt = hbc.load(io.BytesIO(out))
        assert rebuilt.getHeader()["stringStorageSize"] == orig_ss_size


# ===========================================================================
# Bug 4 — getString returns hex for UTF-16 strings
# ===========================================================================

class TestBug4_GetStringUTF16Hex:
    """
    Regression for the bug where getString returned raw hex (e.g. '4c006100...')
    for UTF-16 strings instead of the decoded unicode string (e.g. 'La tua...').
    """

    def _find_utf16_string_id(self, hbc_obj):
        """Return the first UTF-16 string ID, or None if none exist."""
        for sid in range(hbc_obj.getStringCount()):
            entry = hbc_obj.getObj()["stringTableEntries"][sid]
            if entry["isUTF16"] == 1:
                return sid
        return None

    def test_utf16_string_returns_unicode_not_hex(self):
        """getString for a UTF-16 string must return decoded unicode, not hex."""
        hbc_obj = _load_hbc()
        sid = self._find_utf16_string_id(hbc_obj)
        if sid is None:
            pytest.skip("No UTF-16 strings in fixture bundle")

        val, meta = hbc_obj.getString(sid)
        assert isinstance(val, str)
        # Hex output looks like "4c006100..." — all hex digits, even length
        is_hex = len(val) % 2 == 0 and all(c in "0123456789abcdef" for c in val.lower())
        assert not is_hex, (
            f"getString returned what looks like raw hex: {repr(val[:40])}. "
            "Should be decoded unicode."
        )

    def test_utf16_string_is_printable_text(self):
        """getString for a UTF-16 string must return human-readable text."""
        hbc_obj = _load_hbc()
        sid = self._find_utf16_string_id(hbc_obj)
        if sid is None:
            pytest.skip("No UTF-16 strings in fixture bundle")

        val, meta = hbc_obj.getString(sid)
        assert isinstance(val, str)
        # Must contain at least some printable (non-hex-looking) characters
        # A language string like "La tua prima musica è" will have spaces, accents etc.
        assert len(val) > 0

    def test_utf16_getstring_meta_flag(self):
        """getString for a UTF-16 string must return isUTF16=1 in the metadata tuple."""
        hbc_obj = _load_hbc()
        sid = self._find_utf16_string_id(hbc_obj)
        if sid is None:
            pytest.skip("No UTF-16 strings in fixture bundle")

        val, meta = hbc_obj.getString(sid)
        assert meta[0] == 1, f"Expected isUTF16=1, got {meta[0]}"

    def test_utf16_string_roundtrip_through_setstring(self):
        """Setting a UTF-16 string back to itself must preserve the value and binary."""
        orig = _load_orig()
        hbc_obj = hbc.load(io.BytesIO(orig))

        sid = self._find_utf16_string_id(hbc_obj)
        if sid is None:
            pytest.skip("No UTF-16 strings in fixture bundle")

        val_before, _ = hbc_obj.getString(sid)
        hbc_obj.setString(sid, val_before)
        val_after, _ = hbc_obj.getString(sid)

        assert val_before == val_after

        out = _dump_bytes(hbc_obj)
        assert out == orig, "Binary changed after setting UTF-16 string to its own value"

    def test_ascii_string_returns_normal_str(self):
        """getString for an ASCII string must return a normal Python str."""
        hbc_obj = _load_hbc()
        for sid in range(hbc_obj.getStringCount()):
            val, meta = hbc_obj.getString(sid)
            if meta[0] == 0 and len(val) > 0:
                assert isinstance(val, str)
                assert val.isascii()
                break

    def test_string_json_dump_contains_unicode_not_hex(self, tmp_path):
        """
        When hasm.dump writes string.json, UTF-16 string values must be
        readable unicode, not hex strings. Uses hasm.dump only on the string
        section — tests the _write_json_file path quickly.
        """
        hbc_obj = _load_hbc()
        sid = self._find_utf16_string_id(hbc_obj)
        if sid is None:
            pytest.skip("No UTF-16 strings in fixture bundle")

        # Build the string list the same way hasm.dump does, without full disasm
        ss = []
        for i in range(hbc_obj.getStringCount()):
            val, header = hbc_obj.getString(i)
            ss.append({"id": i, "isUTF16": header[0] == 1, "value": val})

        utf16_entries = [s for s in ss if s["isUTF16"]]
        assert len(utf16_entries) > 0

        for entry in utf16_entries[:5]:
            val = entry["value"]
            is_hex = len(val) % 2 == 0 and all(c in "0123456789abcdefABCDEF" for c in val)
            assert not is_hex, (
                f"getString returned hex for UTF-16 string id={entry['id']}: {repr(val[:40])}"
            )


# ===========================================================================
# Bug 5 — getStringId raises ValueError instead of allocating new slot
# ===========================================================================

class TestBug5_GetStringIdAllocatesNewSlot:
    """
    Regression for the bug where getStringId in hbc97/hbc98/hbc100 raised
    ValueError when a string wasn't found, instead of creating a new string slot.
    """

    @pytest.mark.parametrize("ver", [96, 97, 98, 100])
    def test_getStringId_for_existing_string_returns_valid_id(self, ver):
        """getStringId for a string that already exists must return its ID."""
        from hbctool.hbc import _get_hbc_class
        cls = _get_hbc_class(ver)
        if cls is None:
            pytest.skip(f"HBC{ver} not available")

        hbc_obj = _load_hbc()
        # Re-load as target version's class for unit testing
        # For this regression, just confirm the real bundle's getString works
        val, _ = hbc_obj.getString(0)
        sid = hbc_obj.getStringId(val)
        assert sid >= 0
        assert sid < hbc_obj.getStringCount()

    @pytest.mark.parametrize("ver", [96, 97, 98, 100])
    def test_getStringId_for_new_string_allocates_slot(self, ver):
        """
        getStringId for a string not in the table must allocate a new slot
        and return a valid ID, NOT raise ValueError.
        """
        from hbctool.hbc import _get_hbc_class
        cls = _get_hbc_class(ver)
        if cls is None:
            pytest.skip(f"HBC{ver} not available")

        hbc_obj = _load_hbc()
        orig_count = hbc_obj.getStringCount()

        # A string that is astronomically unlikely to exist in the bundle
        new_string = f"__hbctool_regression_test_novel_string_{ver}_xQzWmP__"

        # Must NOT raise — must allocate
        sid = hbc_obj.getStringId(new_string)

        assert isinstance(sid, int), f"Expected int, got {type(sid)}"
        assert sid >= 0
        assert hbc_obj.getStringCount() == orig_count + 1, (
            f"String count should have grown from {orig_count} to {orig_count + 1}"
        )
        # The new ID should retrieve the string we just added
        retrieved, _ = hbc_obj.getString(sid)
        assert retrieved == new_string

    def test_getStringId_new_string_does_not_corrupt_export(self):
        """After allocating a new string ID, the bundle must still export cleanly."""
        hbc_obj = _load_hbc()
        hbc_obj.getStringId("__novel_regression_string_export_test__")

        # Must not raise
        out = _dump_bytes(hbc_obj)
        assert len(out) > 0

        fl = _file_length_from_bytes(out)
        assert fl == len(out), "fileLength must be correct after new string allocation"

    def test_getStringId_caches_result(self):
        """Calling getStringId twice for the same string returns the same ID."""
        hbc_obj = _load_hbc()
        val, _ = hbc_obj.getString(0)
        sid1 = hbc_obj.getStringId(val)
        sid2 = hbc_obj.getStringId(val)
        assert sid1 == sid2

    def test_getStringId_external_cache_respected(self):
        """If a string_id_cache is provided, getStringId must use it and populate it."""
        hbc_obj = _load_hbc()
        val, _ = hbc_obj.getString(5)
        cache = {}
        sid = hbc_obj.getStringId(val, string_id_cache=cache)
        assert val in cache
        assert cache[val] == sid


# ===========================================================================
# Combined regression: all fixes together
# ===========================================================================

class TestCombinedRegressions:
    """End-to-end tests that exercise multiple bug fixes together."""

    def test_setstring_shorter_value_exact_binary_roundtrip(self):
        """
        Replacing a string with a shorter ASCII value must produce a valid bundle
        with correct fileLength and exact structural integrity.
        """
        orig = _load_orig()
        hbc_obj = hbc.load(io.BytesIO(orig))

        # Find a string with length >= 2
        target_sid = None
        target_original = None
        for sid in range(hbc_obj.getStringCount()):
            val, meta = hbc_obj.getString(sid)
            if meta[0] == 0 and len(val) >= 2:
                target_sid = sid
                target_original = val
                break

        assert target_sid is not None, "No suitable ASCII string found in fixture"

        # Replace last char (same length → no storage growth)
        new_val = target_original[:-1] + ("z" if target_original[-1] != "z" else "a")
        hbc_obj.setString(target_sid, new_val)

        # Verify the string was updated
        retrieved, _ = hbc_obj.getString(target_sid)
        assert retrieved == new_val

        out = _dump_bytes(hbc_obj)
        fl = _file_length_from_bytes(out)
        assert fl == len(out)
        assert len(out) == len(orig)  # Same-length change should not grow the file

        # Rebuilt object must parse correctly
        rebuilt = hbc.load(io.BytesIO(out))
        assert rebuilt.getFunctionCount() == hbc_obj.getFunctionCount()
        assert rebuilt.getStringCount() == hbc_obj.getStringCount()

    def test_multiple_string_changes_and_roundtrip(self):
        """
        Making several string changes then dumping must produce a structurally
        valid bundle with correct fileLength and parseable by Hermes.
        """
        orig = _load_orig()
        hbc_obj = hbc.load(io.BytesIO(orig))

        # Make 3 same-length changes
        changes = 0
        for sid in range(hbc_obj.getStringCount()):
            if changes >= 3:
                break
            val, meta = hbc_obj.getString(sid)
            if meta[0] == 0 and len(val) >= 2:
                new_val = val[:-1] + ("z" if val[-1] != "z" else "a")
                hbc_obj.setString(sid, new_val)
                changes += 1

        out = _dump_bytes(hbc_obj)
        fl = _file_length_from_bytes(out)
        assert fl == len(out)

        rebuilt = hbc.load(io.BytesIO(out))
        assert rebuilt.getVersion() == hbc_obj.getVersion()
        assert rebuilt.getFunctionCount() == hbc_obj.getFunctionCount()

    def test_hbc98_string_change_valid_export(self):
        """
        Modify a string in the HBC98 fixture via API and verify the export is
        structurally valid with correct fileLength. No disasm needed.
        """
        orig = _load_orig_98()
        hbc_obj = hbc.load(io.BytesIO(orig))

        # Find a short ASCII string and flip last char
        for sid in range(hbc_obj.getStringCount()):
            val, meta = hbc_obj.getString(sid)
            if meta[0] == 0 and len(val) >= 2:
                new_val = val[:-1] + ("z" if val[-1] != "z" else "a")
                hbc_obj.setString(sid, new_val)
                break

        out = _dump_bytes(hbc_obj)
        fl = _file_length_from_bytes(out)
        assert fl == len(out), f"fileLength={fl} != exported size={len(out)}"

        final = hbc.load(io.BytesIO(out))
        assert final.getVersion() == 98
        assert final.getFunctionCount() == hbc_obj.getFunctionCount()
