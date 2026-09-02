import copy
from hbctool.util import *  # noqa: F403
import hbctool.compat_json as json
import pathlib

from hbctool.util import *  # noqa: F403

basepath = pathlib.Path(__file__).parent.absolute()

MAGIC = 2240826417119764422
BYTECODE_ALIGNMENT = 4

INVALID_OFFSET = 1 << 23
INVALID_LENGTH = (1 << 8) - 1

with open(basepath / "data" / "structure.json", "r") as f:
    structure = json.load(f)

headerS = structure["header"]
smallFunctionHeaderS = structure["SmallFuncHeader"]
functionHeaderS = structure["FuncHeader"]
stringTableEntryS = structure["SmallStringTableEntry"]
overflowStringTableEntryS = structure["OverflowStringTableEntry"]
stringStorageS = structure["StringStorage"]
arrayBufferS = structure["ArrayBuffer"]
objKeyBufferS = structure["ObjKeyBuffer"]
objValueBufferS = structure["ObjValueBuffer"]
regExpTableEntryS = structure["RegExpTableEntry"]
regExpStorageS = structure["RegExpStorage"]
cjsModuleTableS = structure["CJSModuleTable"]


def align(f):
    f.pad(BYTECODE_ALIGNMENT)


def parse(f):
    obj = {}

    # Segment 1: Header
    header = {}
    for key in headerS:
        header[key] = read(f, headerS[key])

    obj["header"] = header
    align(f)

    # Segment 2: Function Header
    functionHeaders = []
    for i in range(header["functionCount"]):
        functionHeader = {}
        for key in smallFunctionHeaderS:
            functionHeader[key] = read(f, smallFunctionHeaderS[key])

        if (functionHeader["flags"] >> 5) & 1:
            functionHeader["small"] = copy.deepcopy(functionHeader)
            saved_pos = f.tell()
            large_offset = (functionHeader["infoOffset"] << 16) | functionHeader[
                "offset"
            ]
            f.seek(large_offset)
            for key in functionHeaderS:
                functionHeader[key] = read(f, functionHeaderS[key])

            f.seek(saved_pos)

        functionHeaders.append(functionHeader)

    obj["functionHeaders"] = functionHeaders
    align(f)

    # Segment 3: StringKind
    # FIXME : Do nothing just skip
    stringKinds = []
    for _ in range(header["stringKindCount"]):
        stringKinds.append(readuint(f, bits=32))

    obj["stringKinds"] = stringKinds
    align(f)

    # Segment 3: IdentifierHash
    # FIXME : Do nothing just skip
    identifierTranslations = []
    for _ in range(header["identifierCount"]):
        identifierTranslations.append(readuint(f, bits=32))

    obj["identifierTranslations"] = identifierTranslations
    align(f)

    # Segment 4: StringTable
    stringTableEntries = []
    for _ in range(header["stringCount"]):
        stringTableEntry = {}
        for key in stringTableEntryS:
            stringTableEntry[key] = read(f, stringTableEntryS[key])

        stringTableEntries.append(stringTableEntry)

    obj["stringTableEntries"] = stringTableEntries
    align(f)

    # Segment 5: StringTableOverflow
    stringTableOverflowEntries = []
    for _ in range(header["overflowStringCount"]):
        stringTableOverflowEntry = {}
        for key in overflowStringTableEntryS:
            stringTableOverflowEntry[key] = read(f, overflowStringTableEntryS[key])

        stringTableOverflowEntries.append(stringTableOverflowEntry)

    obj["stringTableOverflowEntries"] = stringTableOverflowEntries
    align(f)

    # Segment 6: StringStorage
    stringStorage = read(f, [stringStorageS[0], stringStorageS[1], header["stringStorageSize"]])

    obj["stringStorage"] = stringStorage
    align(f)

    # Segment 7: ArrayBuffer
    arrayBuffer = read(f, [arrayBufferS[0], arrayBufferS[1], header["arrayBufferSize"]])

    obj["arrayBuffer"] = arrayBuffer
    align(f)

    # Segment 9: ObjKeyBuffer
    objKeyBuffer = read(f, [objKeyBufferS[0], objKeyBufferS[1], header["objKeyBufferSize"]])

    obj["objKeyBuffer"] = objKeyBuffer
    align(f)

    # Segment 10: ObjValueBuffer
    objValueBuffer = read(f, [objValueBufferS[0], objValueBufferS[1], header["objValueBufferSize"]])

    obj["objValueBuffer"] = objValueBuffer
    align(f)

    # Segment 11: RegExpTable
    regExpTable = []
    for _ in range(header["regExpCount"]):
        regExpEntry = {}
        for key in regExpTableEntryS:
            regExpEntry[key] = read(f, regExpTableEntryS[key])

        regExpTable.append(regExpEntry)

    obj["regExpTable"] = regExpTable
    align(f)

    # Segment 12: RegExpStorage
    regExpStorage = read(f, [regExpStorageS[0], regExpStorageS[1], header["regExpStorageSize"]])

    obj["regExpStorage"] = regExpStorage
    align(f)

    # Segment 13: CJSModuleTable
    cjsModuleTable = []
    for _ in range(header["cjsModuleCount"]):
        cjsModuleEntry = {}
        for key in cjsModuleTableS:
            cjsModuleEntry[key] = read(f, cjsModuleTableS[key])

        cjsModuleTable.append(cjsModuleEntry)

    obj["cjsModuleTable"] = cjsModuleTable
    align(f)

    obj["instOffset"] = f.tell()
    obj["inst"] = f.readall()

    return obj


def export(obj, f):
    # Segment 1: Header
    header = obj["header"]
    # Record the byte offset of fileLength field so we can patch it at end
    # magic(8) + version(4) + sourceHash(20) = 32 bytes => fileLength starts at byte 32
    file_length_offset = 32
    for key in headerS:
        write(f, header[key], headerS[key])

    align(f)

    # Segment 2: Function Header
    functionHeaders = obj["functionHeaders"]
    for i in range(header["functionCount"]):
        functionHeader = functionHeaders[i]
        small = functionHeader.get("small", functionHeader)
        for key in smallFunctionHeaderS:
            write(f, small[key], smallFunctionHeaderS[key])

    align(f)

    # Segment 3: StringKind
    # FIXME : Do nothing just skip
    stringKinds = obj["stringKinds"]
    for i in range(header["stringKindCount"]):
        writeuint(f, stringKinds[i], bits=32)

    align(f)

    # Segment 3: IdentifierHash
    # FIXME : Do nothing just skip
    identifierTranslations = obj["identifierTranslations"]
    for i in range(header["identifierCount"]):
        writeuint(f, identifierTranslations[i], bits=32)

    align(f)

    # Segment 4: StringTable
    stringTableEntries = obj["stringTableEntries"]
    for i in range(header["stringCount"]):
        stringTableEntry = stringTableEntries[i]
        for key in stringTableEntryS:
            write(f, stringTableEntry[key], stringTableEntryS[key])

    align(f)

    # Segment 5: StringTableOverflow
    stringTableOverflowEntries = obj["stringTableOverflowEntries"]
    for i in range(header["overflowStringCount"]):
        stringTableOverflowEntry = stringTableOverflowEntries[i]
        for key in overflowStringTableEntryS:
            write(f, stringTableOverflowEntry[key], overflowStringTableEntryS[key])

    align(f)

    # Segment 6: StringStorage
    stringStorage = obj["stringStorage"]
    write(f, stringStorage, [stringStorageS[0], stringStorageS[1], header["stringStorageSize"]])

    align(f)

    # Segment 7: ArrayBuffer
    arrayBuffer = obj["arrayBuffer"]
    write(f, arrayBuffer, [arrayBufferS[0], arrayBufferS[1], header["arrayBufferSize"]])

    align(f)

    # Segment 9: ObjKeyBuffer
    objKeyBuffer = obj["objKeyBuffer"]
    write(f, objKeyBuffer, [objKeyBufferS[0], objKeyBufferS[1], header["objKeyBufferSize"]])

    align(f)

    # Segment 10: ObjValueBuffer
    objValueBuffer = obj["objValueBuffer"]
    write(f, objValueBuffer, [objValueBufferS[0], objValueBufferS[1], header["objValueBufferSize"]])

    align(f)

    # Segment 11: RegExpTable
    regExpTable = obj["regExpTable"]
    for i in range(header["regExpCount"]):
        regExpEntry = regExpTable[i]
        for key in regExpTableEntryS:
            write(f, regExpEntry[key], regExpTableEntryS[key])

    align(f)

    # Segment 12: RegExpStorage
    regExpStorage = obj["regExpStorage"]
    write(f, regExpStorage, [regExpStorageS[0], regExpStorageS[1], header["regExpStorageSize"]])

    align(f)

    # Segment 13: CJSModuleTable
    cjsModuleTable = obj["cjsModuleTable"]
    for i in range(header["cjsModuleCount"]):
        cjsModuleEntry = cjsModuleTable[i]
        for key in cjsModuleTableS:
            write(f, cjsModuleEntry[key], cjsModuleTableS[key])

    align(f)

    # Write remaining
    f.writeall(obj["inst"])

    # Patch fileLength in the header (at byte offset 32) with the exact output size
    total_size = f.tell()
    header["fileLength"] = total_size
    saved_pos = f.tell()
    f.seek(file_length_offset)
    import struct
    f.out.write(struct.pack("<I", total_size))
    f.seek(saved_pos)


