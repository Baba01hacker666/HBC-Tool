
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
    globals()[hbc_class_name] = hbc_class
    return hbc_class


class _LazyHBCMap(dict):
    def __init__(self, modules):
        super().__init__({version: None for version in modules})
        self._modules = modules

    def __getitem__(self, version):
        if version not in self._modules:
            raise KeyError(version)
        hbc_class = dict.get(self, version)
        if hbc_class is None:
            hbc_class = _get_hbc_class(version)
            dict.__setitem__(self, version, hbc_class)
        return hbc_class

    def get(self, version, default=None):
        try:
            return self[version]
        except KeyError:
            return default

    def items(self):
        for version in self.keys():
            yield version, self[version]

    def values(self):
        for version in self.keys():
            yield self[version]


HBC = _LazyHBCMap(_HBC_MODULES)


def __getattr__(name):
    if name.startswith("HBC") and name[3:].isdigit():
        version = int(name[3:])
        hbc_class = _get_hbc_class(version)
        if hbc_class is None:
            raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
        return hbc_class
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "MAGIC",
    "PLAIN_JS_PREFIX_MAGIC",
    "INIT_HEADER",
    "BYTECODE_ALIGNMENT",
    "HBC",
    "load",
    "loado",
    "dump",
    "dumpo",
] + [f"HBC{version}" for version in sorted(_HBC_MODULES)]

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
