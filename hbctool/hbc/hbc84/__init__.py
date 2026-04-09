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
IntegerTag = 7 << 4
TagMask = 0x70

class HBC84:
    def __init__(self, f=None):
        if f:
            self.obj = parse(f)
        else:
            self.obj = None

    def export(self, f):
        export(self.getObj(), f)

    def getObj(self):
        assert self.obj, "Obj is not set."
        return self.obj

    def setObj(self, obj):
        self.obj = obj

    def getVersion(self):
        return 84

    def getHeader(self):
        return self.getObj()["header"]

    def getFunctionCount(self):
        return self.getObj()["header"]["functionCount"]

    def getFunction(self, fid, disasm=True):
        assert fid >= 0 and fid < self.getFunctionCount(), "Invalid function ID"

        functionHeader = self.getObj()["functionHeaders"][fid]
        offset = functionHeader["offset"]
        paramCount = functionHeader["paramCount"]
        registerCount = functionHeader["frameSize"]
        symbolCount = functionHeader["environmentSize"]
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

        return functionNameStr, paramCount, registerCount, symbolCount, insts, functionHeader
    
    def setFunction(self, fid, func, disasm=True, offset_shift=0, string_id_cache=None):
        assert fid >= 0 and fid < self.getFunctionCount(), "Invalid function ID"

        functionName, paramCount, registerCount, symbolCount, insts, _ = func

        functionHeader = self.getObj()["functionHeaders"][fid]

        functionHeader["paramCount"] = paramCount
        functionHeader["frameSize"] = registerCount
        functionHeader["environmentSize"] = symbolCount

        functionHeader["functionName"] = self.getStringId(functionName, string_id_cache=string_id_cache)

        offset = functionHeader["offset"]
        bytecodeSizeInBytes = functionHeader["bytecodeSizeInBytes"]

        instOffset = self.getObj()["instOffset"]
        start = offset - instOffset + offset_shift
        
        bc = insts

        if disasm:
            bc = assemble(insts)
            
        if len(bc) > bytecodeSizeInBytes:
            self.getObj()["inst"][start:start + bytecodeSizeInBytes] = bc
        else:
            memcpy(self.getObj()["inst"], bc, start, len(bc))
            if len(bc) < bytecodeSizeInBytes:
                del self.getObj()["inst"][start + len(bc):start + bytecodeSizeInBytes]

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

        new_inst = []
        current_offset = self.getObj()["instOffset"]
        for function_header, chunk in zip(function_headers, chunks):
            function_header["offset"] = current_offset
            function_header["bytecodeSizeInBytes"] = len(chunk)
            new_inst.extend(chunk)
            current_offset += len(chunk)

        self.getObj()["inst"] = new_inst

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
    def getStringId(self, string_value, string_id_cache=None):
        from .parser import INVALID_LENGTH
        count = self.getStringCount()
        if string_id_cache is not None:
            sid = string_id_cache.get(string_value)
            if sid is not None:
                return sid
        for i in range(count):
            s, _ = self.getString(i)
            if s == string_value:
                if string_id_cache is not None:
                    string_id_cache[string_value] = i
                return i

        isUTF16 = 0
        s = string_value.encode("utf-8")
        l = len(s)

        offset = self._allocate_string_slot(len(s))

        stringTableEntry = {
            "isUTF16": isUTF16,
        }

        stringTableOverflowEntries = self.getObj()["stringTableOverflowEntries"]
        if l >= INVALID_LENGTH:
            stringTableEntry["length"] = INVALID_LENGTH
            stringTableEntry["offset"] = len(stringTableOverflowEntries)
            stringTableOverflowEntries.append({"offset": offset, "length": l})
            self.getObj()["header"]["overflowStringCount"] = len(stringTableOverflowEntries)
        else:
            stringTableEntry["length"] = l
            stringTableEntry["offset"] = offset

        self.getObj()["stringTableEntries"].append(stringTableEntry)
        self.getObj()["header"]["stringCount"] += 1

        stringStorage = self.getObj()["stringStorage"]
        from hbctool.util import memcpy
        memcpy(stringStorage, s, offset, len(s))

        if string_id_cache is not None:
            string_id_cache[string_value] = count

        return count


    def getStringCount(self):
        return self.getObj()["header"]["stringCount"]

    def getString(self, sid):
        assert sid >= 0 and sid < self.getStringCount(), "Invalid string ID"

        stringTableEntry = self.getObj()["stringTableEntries"][sid]
        stringStorage = self.getObj()["stringStorage"]
        stringTableOverflowEntries = self.getObj()["stringTableOverflowEntries"]

        isUTF16 = stringTableEntry["isUTF16"]
        offset = stringTableEntry["offset"]
        length = stringTableEntry["length"]

        if length >= INVALID_LENGTH:
            stringTableOverflowEntry = stringTableOverflowEntries[offset]
            offset = stringTableOverflowEntry["offset"]
            length = stringTableOverflowEntry["length"]

        if isUTF16:
            length*=2

        s = bytes(stringStorage[offset:offset + length])
        return s.hex() if isUTF16 else s.decode("utf-8"), (isUTF16, offset, length)
    
    def setString(self, sid, val):
        assert sid >= 0 and sid < self.getStringCount(), "Invalid string ID"

        stringTableEntry = self.getObj()["stringTableEntries"][sid]
        stringStorage = self.getObj()["stringStorage"]
        stringTableOverflowEntries = self.getObj()["stringTableOverflowEntries"]

        isUTF16 = stringTableEntry["isUTF16"]
        offset = stringTableEntry["offset"]
        length = stringTableEntry["length"]

        if length >= INVALID_LENGTH:
            stringTableOverflowEntry = stringTableOverflowEntries[offset]
            offset = stringTableOverflowEntry["offset"]
            length = stringTableOverflowEntry["length"]
        
        if isUTF16:
            s = list(bytes.fromhex(val))
            l = len(s)//2
        else:
            l = len(val)
            s = val.encode("utf-8")
        
        if l > length:
            offset = self._allocate_string_slot(len(s))
            if stringTableEntry["length"] >= INVALID_LENGTH:
                stringTableOverflowEntries[stringTableEntry["offset"]]["offset"] = offset
                stringTableOverflowEntries[stringTableEntry["offset"]]["length"] = l
            else:
                stringTableEntry["length"] = INVALID_LENGTH
                stringTableEntry["offset"] = len(stringTableOverflowEntries)
                stringTableOverflowEntries.append({"offset": offset, "length": l})
                self.getObj()["header"]["overflowStringCount"] = len(stringTableOverflowEntries)
        else:
            if isUTF16:
                length *= 2

        memcpy(stringStorage, s, offset, len(s))
        
    def _checkBufferTag(self, buf, iid):
        keyTag = buf[iid]
        if keyTag & 0x80:
            return (((keyTag & 0x0f) << 8) | (buf[iid + 1]), keyTag & TagMask)
        else:
            return (keyTag & 0x0f, keyTag & TagMask)

    def _SLPToString(self, tag, buf, iid, ind):
        start = iid + ind
        if tag == ByteStringTag:
            type = "String"
            val = buf[start]
            ind += 1
        elif tag == ShortStringTag:
            type = "String"
            val = unpack("<H", bytes(buf[start:start+2]))[0]
            ind += 2
        elif tag == LongStringTag:
            type = "String"
            val = unpack("<L", bytes(buf[start:start+4]))[0]
            ind += 4
        elif tag == NumberTag:
            type = "Number"
            val = unpack("<d", bytes(buf[start:start+8]))[0]
            ind += 8
        elif tag == IntegerTag:
            type = "Integer"
            val = unpack("<L", bytes(buf[start:start+4]))[0]
            ind += 4
        elif tag == NullTag:
            type = "Null"
            val = None
        elif tag == TrueTag:
            type = "Boolean"
            val = True
        elif tag == FalseTag:
            type = "Boolean"
            val = False
        else:
            type = "Empty"
            val = None
        
        return type, val, ind

    def getArrayBufferSize(self):
        return self.getObj()["header"]["arrayBufferSize"]

    def getArray(self, aid):
        assert aid >= 0 and aid < self.getArrayBufferSize(), "Invalid Array ID"
        tag = self._checkBufferTag(self.getObj()["arrayBuffer"], aid)
        ind = 2 if tag[0] > 0x0f else 1
        arr = []
        t = None
        for _ in range(tag[0]):
            t, val, ind = self._SLPToString(tag[1], self.getObj()["arrayBuffer"], aid, ind)
            arr.append(val)
        
        return t, arr

    def getObjKeyBufferSize(self):
        return self.getObj()["header"]["objKeyBufferSize"]

    def getObjKey(self, kid):
        assert kid >= 0 and kid < self.getObjKeyBufferSize(), "Invalid ObjKey ID"
        tag = self._checkBufferTag(self.getObj()["objKeyBuffer"], kid)
        ind = 2 if tag[0] > 0x0f else 1
        keys = []
        t = None
        for _ in range(tag[0]):
            t, val, ind = self._SLPToString(tag[1], self.getObj()["objKeyBuffer"], kid, ind)
            keys.append(val)
        
        return t, keys

    def getObjValueBufferSize(self):
        return self.getObj()["header"]["objValueBufferSize"]

    def getObjValue(self, vid):
        assert vid >= 0 and vid < self.getObjValueBufferSize(), "Invalid ObjValue ID"
        tag = self._checkBufferTag(self.getObj()["objValueBuffer"], vid)
        ind = 2 if tag[0] > 0x0f else 1
        keys = []
        t = None
        for _ in range(tag[0]):
            t, val, ind = self._SLPToString(tag[1], self.getObj()["objValueBuffer"], vid, ind)
            keys.append(val)
        
        return t, keys
