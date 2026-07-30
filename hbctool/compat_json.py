import sys

_engine = "json"
_json_module = None

import json
_json_module = json

try:
    import ujson
    _json_module = ujson
    _engine = "ujson"
except ImportError:
    pass

def enable_orjson():
    global _engine
    global _json_module
    try:
        import orjson
        _json_module = orjson
        _engine = "orjson"
    except ImportError:
        print("[!] --fast-json requested but 'orjson' is not installed. Please run: pip install orjson", file=sys.stderr)
        sys.exit(1)

def load(f):
    if _engine == "orjson":
        return _json_module.loads(f.read())
    return _json_module.load(f)

def dump(obj, f, indent=None, ensure_ascii=False):
    if _engine == "orjson":
        option = 0
        if indent:
            option |= _json_module.OPT_INDENT_2
        f.write(_json_module.dumps(obj, option=option).decode('utf-8'))
    elif _engine == "ujson":
        if indent is True: indent_val = 4
        elif indent is False or indent is None: indent_val = 0
        else: indent_val = indent
        _json_module.dump(obj, f, indent=indent_val, ensure_ascii=ensure_ascii)
    else:
        _json_module.dump(obj, f, indent=indent, ensure_ascii=ensure_ascii)

def dumps(obj, **kwargs):
    if _engine == "orjson":
        option = 0
        if kwargs.get('indent'):
            option |= _json_module.OPT_INDENT_2
        return _json_module.dumps(obj, option=option).decode('utf-8')
    elif _engine == "ujson":
        if 'indent' in kwargs:
            if kwargs['indent'] is True: kwargs['indent'] = 4
            elif kwargs['indent'] is False or kwargs['indent'] is None: kwargs['indent'] = 0
        return _json_module.dumps(obj, **kwargs)
    else:
        return _json_module.dumps(obj, **kwargs)

def loads(s, **kwargs):
    if _engine == "orjson":
        return _json_module.loads(s)
    return _json_module.loads(s, **kwargs)
