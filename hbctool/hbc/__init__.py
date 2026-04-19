
import importlib

from hbctool.util import *

MAGIC = 2240826417119764422
PLAIN_JS_PREFIX_MAGIC = int.from_bytes(b"var __BU", "little")
INIT_HEADER = {
    "magic": ["uint", 64, 1],
    "version": ["uint", 32, 1]
}
BYTECODE_ALIGNMENT = 4

_HBC_MODULES = {
    96: "hbctool.hbc.hbc96",
    95: "hbctool.hbc.hbc95",
    94: "hbctool.hbc.hbc94",
    93: "hbctool.hbc.hbc93",
    92: "hbctool.hbc.hbc92",
    91: "hbctool.hbc.hbc91",
    90: "hbctool.hbc.hbc90",
    89: "hbctool.hbc.hbc89",
    88: "hbctool.hbc.hbc88",
    87: "hbctool.hbc.hbc87",
    86: "hbctool.hbc.hbc86",
    85: "hbctool.hbc.hbc85",
    84: "hbctool.hbc.hbc84",
    83: "hbctool.hbc.hbc83",
    76: "hbctool.hbc.hbc76",
    74: "hbctool.hbc.hbc74",
    62: "hbctool.hbc.hbc62",
    59: "hbctool.hbc.hbc59",
}
_HBC_CLASS_CACHE = {}


def _get_hbc_class(version):
    hbc_class = _HBC_CLASS_CACHE.get(version)
    if hbc_class is not None:
        return hbc_class

    module_name = _HBC_MODULES.get(version)
    if module_name is None:
        return None

    module = importlib.import_module(module_name)
    hbc_class_name = f"HBC{version}"
    hbc_class = getattr(module, hbc_class_name)
    _HBC_CLASS_CACHE[version] = hbc_class
    return hbc_class

def load(f):
    f = BitReader(f)
    magic = read(f, INIT_HEADER["magic"])
    version = read(f, INIT_HEADER["version"])
    f.seek(0)
    if magic != MAGIC:
        if magic == PLAIN_JS_PREFIX_MAGIC:
            raise ValueError(
                "The input appears to be a plain JavaScript Metro bundle, not Hermes bytecode. "
                "Enable Hermes when building the app and use the generated Hermes bytecode bundle."
            )
        raise ValueError(f"The magic ({hex(magic)}) is invalid. (must be {hex(MAGIC)})")
    hbc_class = _get_hbc_class(version)
    if hbc_class is None:
        raise ValueError(f"The HBC version ({version}) is not supported.")

    return hbc_class(f)

def loado(obj):
    magic = obj["header"]["magic"]
    version = obj["header"]["version"]

    if magic != MAGIC:
        if magic == PLAIN_JS_PREFIX_MAGIC:
            raise ValueError(
                "The input appears to be a plain JavaScript Metro bundle, not Hermes bytecode. "
                "Enable Hermes when building the app and use the generated Hermes bytecode bundle."
            )
        raise ValueError(f"The magic ({hex(magic)}) is invalid. (must be {hex(MAGIC)})")
    hbc_class = _get_hbc_class(version)
    if hbc_class is None:
        raise ValueError(f"The HBC version ({version}) is not supported.")

    hbc = hbc_class()
    hbc.setObj(obj)
    return hbc

def dump(hbc, f):
    f = BitWriter(f)
    hbc.export(f)

def dumpo(hbc):
    return hbc.getObj()
