from hbctool.util import *  # noqa: F403

from .parser import INVALID_LENGTH, export, parse
from .translator import assemble, disassemble

NullTag = 0
TrueTag = 1 << 4
FalseTag = 2 << 4
NumberTag = 3 << 4
LongStringTag = 4 << 4
ShortStringTag = 5 << 4
ByteStringTag = 6 << 4

TagMask = 0x70


class HBC98:
    def __init__(self, f=None):
        self._string_id_cache = {}
        self._last_string_id_searched = -1

        if f is not None:
            self.obj = parse(f)
        else:
            self.obj = None

    def setObj(self, obj):
        self.obj = obj
        self._string_id_cache = {}
        self._last_string_id_searched = -1

    def getObj(self):
        return self.obj

    def getVersion(self):
        return 98

    def getHeader(self):
        return self.getObj()["header"]

    def getFunctionCount(self):
        return self.getHeader()["functionCount"]

    def getStringCount(self):
        return self.getHeader()["stringCount"]

    def getString(self, sid):
        assert sid >= 0 and sid < self.getStringCount(), "Invalid string ID"

        stringTableEntry = self.getObj()["stringTableEntries"][sid]
        stringStorage = self.getObj()["stringStorage"]
        stringTableOverflowEntries = self.getObj()["stringTableOverflowEntries"]

        isUTF16 = stringTableEntry["isUTF16"] == 1
        offset = stringTableEntry["offset"]
        length = stringTableEntry["length"]

        if length >= INVALID_LENGTH:
            stringTableOverflowEntry = stringTableOverflowEntries[offset]
            offset = stringTableOverflowEntry["offset"]
            length = stringTableOverflowEntry["length"]

        raw_len = length * 2 if isUTF16 else length
        s = bytes(stringStorage[offset : offset + raw_len])
        return s.hex() if isUTF16 else s.decode("utf-8", errors="surrogateescape"), (1 if isUTF16 else 0, offset, length)

    def getStringId(self, string_value, string_id_cache=None):
        from .parser import INVALID_LENGTH

        count = self.getStringCount()

        sid = self._string_id_cache.get(string_value)
        if sid is not None:
            if string_id_cache is not None:
                string_id_cache[string_value] = sid
            return sid

        if string_id_cache is not None:
            sid = string_id_cache.get(string_value)
            if sid is not None:
                return sid

        for i in range(self._last_string_id_searched + 1, count):
            try:
                s, _ = self.getString(i)
                self._string_id_cache.setdefault(s, i)
                self._last_string_id_searched = i
                if s == string_value:
                    if string_id_cache is not None:
                        string_id_cache[string_value] = i
                    return i
            except UnicodeDecodeError:
                self._last_string_id_searched = i
                continue

        is_utf16 = not string_value.isascii()
        if is_utf16:
            s = string_value.encode("utf-16-le", errors="surrogatepass")
            str_length = len(s) // 2
        else:
            s = string_value.encode("utf-8")
            str_length = len(s)

        offset = self._allocate_string_slot(len(s))

        stringTableEntry = {
            "isUTF16": 1 if is_utf16 else 0,
        }

        stringTableOverflowEntries = self.getObj()["stringTableOverflowEntries"]
        if str_length >= INVALID_LENGTH:
            stringTableEntry["length"] = INVALID_LENGTH
            stringTableEntry["offset"] = len(stringTableOverflowEntries)
            stringTableOverflowEntries.append({"offset": offset, "length": str_length})
            self.getObj()["header"]["overflowStringCount"] = len(
                stringTableOverflowEntries
            )
        else:
            stringTableEntry["length"] = str_length
            stringTableEntry["offset"] = offset

        self.getObj()["stringTableEntries"].append(stringTableEntry)
        self.getObj()["header"]["stringCount"] += 1

        if "stringKinds" in self.getObj():
            stringKinds = self.getObj()["stringKinds"]
            if stringKinds and (stringKinds[-1] & 1 == 0):
                stringKinds[-1] += 1 << 1
            else:
                stringKinds.append(1 << 1)
            if "stringKindCount" in self.getObj().get("header", {}):
                self.getObj()["header"]["stringKindCount"] = len(stringKinds)

        stringStorage = self.getObj()["stringStorage"]
        from hbctool.util import memcpy

        memcpy(stringStorage, s, offset, len(s))

        if string_id_cache is not None:
            string_id_cache[string_value] = count
        self._string_id_cache[string_value] = count

        return count

    def _shift_function_offsets(self, delta):
        if delta == 0:
            return

        for function_header in self.getObj()["functionHeaders"]:
            function_header["offset"] += delta

    def _allocate_string_slot(self, byte_length):
        header = self.getObj()["header"]
        old_size = header["stringStorageSize"]
        new_size = old_size + byte_length
        old_aligned_size = (old_size + 3) & ~0x03
        new_aligned_size = (new_size + 3) & ~0x03
        delta = new_aligned_size - old_aligned_size

        string_storage = self.getObj()["stringStorage"]
        offset = len(string_storage)
        string_storage.extend([0] * byte_length)

        header["stringStorageSize"] = len(string_storage)
        if delta:
            self.getObj()["instOffset"] += delta
            self._shift_function_offsets(delta)

        return offset

    def setString(self, sid, val):
        assert sid >= 0 and sid < self.getStringCount(), "Invalid string ID"

        from .parser import INVALID_LENGTH

        self._string_id_cache = {}
        self._last_string_id_searched = -1

        stringTableEntry = self.getObj()["stringTableEntries"][sid]
        stringStorage = self.getObj()["stringStorage"]
        stringTableOverflowEntries = self.getObj()["stringTableOverflowEntries"]

        isUTF16 = stringTableEntry["isUTF16"] == 1
        offset = stringTableEntry["offset"]
        length = stringTableEntry["length"]

        if length >= INVALID_LENGTH:
            stringTableOverflowEntry = stringTableOverflowEntries[offset]
            offset = stringTableOverflowEntry["offset"]
            length = stringTableOverflowEntry["length"]

        is_utf16 = not val.isascii() if isinstance(val, str) else False
        if is_utf16:
            s = val.encode("utf-16-le") if isinstance(val, str) else val
            l = len(s) // 2
        else:
            s = val.encode("utf-8") if isinstance(val, str) else val
            l = len(s)

        if l > length:
            offset = self._allocate_string_slot(len(s))
            if stringTableEntry["length"] >= INVALID_LENGTH:
                stringTableOverflowEntries[stringTableEntry["offset"]]["offset"] = (
                    offset
                )
                stringTableOverflowEntries[stringTableEntry["offset"]]["length"] = l
            else:
                stringTableEntry["length"] = INVALID_LENGTH
                stringTableEntry["offset"] = len(stringTableOverflowEntries)
                stringTableOverflowEntries.append({"offset": offset, "length": l})
                self.getObj()["header"]["overflowStringCount"] = len(
                    stringTableOverflowEntries
                )
        else:
            stringTableEntry["isUTF16"] = 1 if is_utf16 else 0
            if isUTF16:
                length *= 2

        memcpy(stringStorage, s, offset, len(s))

    def getFunction(self, fid, disasm=True):
        assert fid >= 0 and fid < self.getFunctionCount(), "Invalid function ID"

        functionHeader = self.getObj()["functionHeaders"][fid]
        offset = functionHeader["offset"]
        paramCount = functionHeader["paramCount"]
        registerCount = functionHeader["frameSize"]
        symbolCount = functionHeader.get("environmentSize", functionHeader.get("readCacheSize", 0))
        bytecodeSizeInBytes = functionHeader["bytecodeSizeInBytes"]
        functionName = functionHeader["functionName"]

        instOffset = self.getObj()["instOffset"]
        start = offset - instOffset
        end = start + bytecodeSizeInBytes
        bc = self.getObj()["inst"][start:end]
        insts = bc
        if disasm:
            insts = disassemble(bc)

        functionNameStr, _ = self.getString(functionName)

        return (
            functionNameStr,
            paramCount,
            registerCount,
            symbolCount,
            insts,
            functionHeader,
        )

    def setFunction(self, fid, func, disasm=True, offset_shift=0, string_id_cache=None):
        assert fid >= 0 and fid < self.getFunctionCount(), "Invalid function ID"

        functionName, paramCount, registerCount, symbolCount, insts, _ = func

        functionHeader = self.getObj()["functionHeaders"][fid]

        functionHeader["paramCount"] = paramCount
        functionHeader["frameSize"] = registerCount
        if "environmentSize" in functionHeader:
            functionHeader["environmentSize"] = symbolCount

        functionHeader["functionName"] = self.getStringId(
            functionName, string_id_cache=string_id_cache
        )

        offset = functionHeader["offset"]
        bytecodeSizeInBytes = functionHeader["bytecodeSizeInBytes"]

        instOffset = self.getObj()["instOffset"]
        start = offset - instOffset + offset_shift

        bc = insts

        if disasm:
            bc = assemble(insts)

        if len(bc) > bytecodeSizeInBytes:
            self.getObj()["inst"][start : start + bytecodeSizeInBytes] = bc
        else:
            memcpy(self.getObj()["inst"], bc, start, len(bc))
            if len(bc) < bytecodeSizeInBytes:
                del self.getObj()["inst"][start + len(bc) : start + bytecodeSizeInBytes]

        functionHeader["bytecodeSizeInBytes"] = len(bc)
        return len(bc) - bytecodeSizeInBytes

    def _rebuild_function_offsets(self):
        function_headers = self.getObj()["functionHeaders"]
        chunks = []
        for function_header in function_headers:
            offset = function_header["offset"]
            bytecode_size = function_header["bytecodeSizeInBytes"]
            start = offset - self.getObj()["instOffset"]
            end = start + bytecode_size
            chunks.append(self.getObj()["inst"][start:end])

        current_offset = self.getObj()["instOffset"]
        new_inst = []
        for i, function_header in enumerate(function_headers):
            function_header["offset"] = current_offset
            chunk = chunks[i]
            new_inst.extend(chunk)
            current_offset += len(chunk)

        self.getObj()["inst"] = new_inst

    def export(self, f):
        export(self.getObj(), f)
