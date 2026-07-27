from hbctool.util import *
from .parser import parse, export, INVALID_LENGTH
from .translator import disassemble, assemble
from struct import pack, unpack

NullTag = 0
TrueTag = 1 << 4
FalseTag = 2 << 4
NumberTag = 3 << 4
LongStringTag = 4 << 4
ShortStringTag = 5 << 4
ByteStringTag = 6 << 4

TagMask = 0x70


class HBC97:
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
        return 97

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

    def getStringId(self, s, string_id_cache=None):
        if string_id_cache is not None:
            if s in string_id_cache:
                return string_id_cache[s]
        else:
            if s in self._string_id_cache:
                return self._string_id_cache[s]

            next_search_id = self._last_string_id_searched + 1
            if next_search_id < self.getStringCount():
                val, _ = self.getString(next_search_id)
                self._string_id_cache[val] = next_search_id
                self._last_string_id_searched = next_search_id
                if val == s:
                    return next_search_id

        for i in range(self.getStringCount()):
            val, _ = self.getString(i)
            if string_id_cache is not None:
                string_id_cache[val] = i
            else:
                self._string_id_cache[val] = i
            if val == s:
                return i

        raise ValueError(f"String ID not found: {s}")

    def setString(self, sid, s):
        assert sid >= 0 and sid < self.getStringCount(), "Invalid string ID"

        orig_value, _ = self.getString(sid)
        if s == orig_value:
            return

        is_utf16 = False
        try:
            s.decode("ascii")
        except UnicodeDecodeError:
            is_utf16 = True

        if is_utf16:
            encoded = []
            for char in s.decode("utf-8"):
                cp = ord(char)
                if cp <= 0xFFFF:
                    encoded.extend(pack("<H", cp))
                else:
                    cp -= 0x10000
                    high = 0xD800 + (cp >> 10)
                    low = 0xDC00 + (cp & 0x3FF)
                    encoded.extend(pack("<H", high))
                    encoded.extend(pack("<H", low))
            s = encoded
            length = len(s) // 2
        else:
            length = len(s)

        stringTableEntry = self.getObj()["stringTableEntries"][sid]
        offset = len(self.getObj()["stringStorage"])

        if length >= INVALID_LENGTH:
            stringTableEntry["isUTF16"] = 1 if is_utf16 else 0
            stringTableEntry["offset"] = len(
                self.getObj()["stringTableOverflowEntries"]
            )
            stringTableEntry["length"] = INVALID_LENGTH

            overflowStringTableEntry = {
                "offset": offset,
                "length": length,
            }
            self.getObj()["stringTableOverflowEntries"].append(
                overflowStringTableEntry
            )
            self.getObj()["header"]["overflowStringCount"] += 1
        else:
            stringTableEntry["isUTF16"] = 1 if is_utf16 else 0
            stringTableEntry["offset"] = offset
            stringTableEntry["length"] = length

        self.getObj()["header"]["stringStorageSize"] += len(s)

        stringStorage = self.getObj()["stringStorage"]
        from hbctool.util import memcpy

        memcpy(stringStorage, s, offset, len(s))

        if self._string_id_cache is not None:
            self._string_id_cache[s] = sid

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
