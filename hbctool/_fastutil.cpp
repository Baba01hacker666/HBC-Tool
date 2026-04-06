#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>
#include <string.h>

static int get_u8(PyObject* obj, Py_ssize_t idx, uint8_t* out) {
    if (PyBytes_Check(obj)) {
        Py_ssize_t size = PyBytes_GET_SIZE(obj);
        if (idx < 0 || idx >= size) return -1;
        *out = (uint8_t)PyBytes_AS_STRING(obj)[idx];
        return 0;
    }

    if (PyByteArray_Check(obj)) {
        Py_ssize_t size = PyByteArray_GET_SIZE(obj);
        if (idx < 0 || idx >= size) return -1;
        *out = (uint8_t)PyByteArray_AS_STRING(obj)[idx];
        return 0;
    }

    PyObject* item = PySequence_GetItem(obj, idx);
    if (!item) return -1;
    long v = PyLong_AsLong(item);
    Py_DECREF(item);
    if (PyErr_Occurred()) return -1;
    if (v < 0 || v > 255) {
        PyErr_SetString(PyExc_ValueError, "byte value out of range");
        return -1;
    }
    *out = (uint8_t)v;
    return 0;
}

static PyObject* fu_to_uint8(PyObject*, PyObject* args) {
    PyObject* buf;
    if (!PyArg_ParseTuple(args, "O", &buf)) return nullptr;
    uint8_t b0;
    if (get_u8(buf, 0, &b0) != 0) {
        if (!PyErr_Occurred()) PyErr_SetString(PyExc_IndexError, "buffer too small");
        return nullptr;
    }
    return PyLong_FromUnsignedLong((unsigned long)b0);
}

static PyObject* fu_to_uint16(PyObject*, PyObject* args) {
    PyObject* buf;
    if (!PyArg_ParseTuple(args, "O", &buf)) return nullptr;
    uint8_t b0, b1;
    if (get_u8(buf, 0, &b0) != 0 || get_u8(buf, 1, &b1) != 0) {
        if (!PyErr_Occurred()) PyErr_SetString(PyExc_IndexError, "buffer too small");
        return nullptr;
    }
    uint16_t v = (uint16_t)b0 | ((uint16_t)b1 << 8);
    return PyLong_FromUnsignedLong((unsigned long)v);
}

static PyObject* fu_to_uint32(PyObject*, PyObject* args) {
    PyObject* buf;
    if (!PyArg_ParseTuple(args, "O", &buf)) return nullptr;
    uint8_t b0, b1, b2, b3;
    if (get_u8(buf, 0, &b0) != 0 || get_u8(buf, 1, &b1) != 0 || get_u8(buf, 2, &b2) != 0 || get_u8(buf, 3, &b3) != 0) {
        if (!PyErr_Occurred()) PyErr_SetString(PyExc_IndexError, "buffer too small");
        return nullptr;
    }
    uint32_t v = (uint32_t)b0 | ((uint32_t)b1 << 8) | ((uint32_t)b2 << 16) | ((uint32_t)b3 << 24);
    return PyLong_FromUnsignedLong((unsigned long)v);
}

static PyObject* fu_to_int8(PyObject*, PyObject* args) {
    PyObject* buf;
    if (!PyArg_ParseTuple(args, "O", &buf)) return nullptr;
    uint8_t b0;
    if (get_u8(buf, 0, &b0) != 0) {
        if (!PyErr_Occurred()) PyErr_SetString(PyExc_IndexError, "buffer too small");
        return nullptr;
    }
    int8_t v = (int8_t)b0;
    return PyLong_FromLong((long)v);
}

static PyObject* fu_to_int32(PyObject*, PyObject* args) {
    PyObject* buf;
    if (!PyArg_ParseTuple(args, "O", &buf)) return nullptr;
    uint8_t b0, b1, b2, b3;
    if (get_u8(buf, 0, &b0) != 0 || get_u8(buf, 1, &b1) != 0 || get_u8(buf, 2, &b2) != 0 || get_u8(buf, 3, &b3) != 0) {
        if (!PyErr_Occurred()) PyErr_SetString(PyExc_IndexError, "buffer too small");
        return nullptr;
    }
    int32_t v = (int32_t)((uint32_t)b0 | ((uint32_t)b1 << 8) | ((uint32_t)b2 << 16) | ((uint32_t)b3 << 24));
    return PyLong_FromLong((long)v);
}

static PyObject* fu_to_double(PyObject*, PyObject* args) {
    PyObject* buf;
    if (!PyArg_ParseTuple(args, "O", &buf)) return nullptr;
    uint8_t b[8];
    for (int i = 0; i < 8; ++i) {
        if (get_u8(buf, i, &b[i]) != 0) {
            if (!PyErr_Occurred()) PyErr_SetString(PyExc_IndexError, "buffer too small");
            return nullptr;
        }
    }
    double d;
    memcpy(&d, b, 8);
    return PyFloat_FromDouble(d);
}

static PyObject* list_from_bytes(const uint8_t* p, Py_ssize_t n) {
    PyObject* out = PyList_New(n);
    if (!out) return nullptr;
    for (Py_ssize_t i = 0; i < n; ++i) {
        PyObject* v = PyLong_FromUnsignedLong((unsigned long)p[i]);
        if (!v) { Py_DECREF(out); return nullptr; }
        PyList_SET_ITEM(out, i, v);
    }
    return out;
}

static PyObject* fu_from_uint8(PyObject*, PyObject* args) {
    unsigned long v;
    if (!PyArg_ParseTuple(args, "k", &v)) return nullptr;
    uint8_t b = (uint8_t)(v & 0xFF);
    return list_from_bytes(&b, 1);
}

static PyObject* fu_from_uint16(PyObject*, PyObject* args) {
    unsigned long v;
    if (!PyArg_ParseTuple(args, "k", &v)) return nullptr;
    uint8_t b[2] = {(uint8_t)(v & 0xFF), (uint8_t)((v >> 8) & 0xFF)};
    return list_from_bytes(b, 2);
}

static PyObject* fu_from_uint32(PyObject*, PyObject* args) {
    unsigned long v;
    if (!PyArg_ParseTuple(args, "k", &v)) return nullptr;
    uint8_t b[4] = {
        (uint8_t)(v & 0xFF),
        (uint8_t)((v >> 8) & 0xFF),
        (uint8_t)((v >> 16) & 0xFF),
        (uint8_t)((v >> 24) & 0xFF)
    };
    return list_from_bytes(b, 4);
}

static PyObject* fu_from_int8(PyObject*, PyObject* args) {
    long v;
    if (!PyArg_ParseTuple(args, "l", &v)) return nullptr;
    int8_t i = (int8_t)v;
    uint8_t b = (uint8_t)i;
    return list_from_bytes(&b, 1);
}

static PyObject* fu_from_int32(PyObject*, PyObject* args) {
    long v;
    if (!PyArg_ParseTuple(args, "l", &v)) return nullptr;
    uint32_t u = (uint32_t)(int32_t)v;
    uint8_t b[4] = {
        (uint8_t)(u & 0xFF),
        (uint8_t)((u >> 8) & 0xFF),
        (uint8_t)((u >> 16) & 0xFF),
        (uint8_t)((u >> 24) & 0xFF)
    };
    return list_from_bytes(b, 4);
}

static PyObject* fu_from_double(PyObject*, PyObject* args) {
    double d;
    if (!PyArg_ParseTuple(args, "d", &d)) return nullptr;
    uint8_t b[8];
    memcpy(b, &d, 8);
    return list_from_bytes(b, 8);
}

static PyObject* fu_memcpy(PyObject*, PyObject* args) {
    PyObject* dest;
    PyObject* src;
    Py_ssize_t start;
    Py_ssize_t length;
    if (!PyArg_ParseTuple(args, "OOnn", &dest, &src, &start, &length)) return nullptr;

    if (!PyList_Check(dest)) {
        PyErr_SetString(PyExc_TypeError, "dest must be a list");
        return nullptr;
    }

    for (Py_ssize_t i = 0; i < length; ++i) {
        PyObject* item = PySequence_GetItem(src, i);
        if (!item) return nullptr;
        long v = PyLong_AsLong(item);
        if (PyErr_Occurred()) { Py_DECREF(item); return nullptr; }
        if (v < 0 || v > 255) {
            Py_DECREF(item);
            PyErr_SetString(PyExc_ValueError, "src item out of byte range");
            return nullptr;
        }
        PyObject* pyv = PyLong_FromLong(v);
        Py_DECREF(item);
        if (!pyv) return nullptr;
        if (PyList_SetItem(dest, start + i, pyv) != 0) {
            Py_DECREF(pyv);
            return nullptr;
        }
    }

    Py_RETURN_NONE;
}

static PyMethodDef FastUtilMethods[] = {
    {"to_uint8", fu_to_uint8, METH_VARARGS, "Convert buffer to uint8."},
    {"to_uint16", fu_to_uint16, METH_VARARGS, "Convert buffer to uint16 (LE)."},
    {"to_uint32", fu_to_uint32, METH_VARARGS, "Convert buffer to uint32 (LE)."},
    {"to_int8", fu_to_int8, METH_VARARGS, "Convert buffer to int8."},
    {"to_int32", fu_to_int32, METH_VARARGS, "Convert buffer to int32 (LE)."},
    {"to_double", fu_to_double, METH_VARARGS, "Convert buffer to double (LE bytes)."},
    {"from_uint8", fu_from_uint8, METH_VARARGS, "Pack uint8 to byte list."},
    {"from_uint16", fu_from_uint16, METH_VARARGS, "Pack uint16 to byte list."},
    {"from_uint32", fu_from_uint32, METH_VARARGS, "Pack uint32 to byte list."},
    {"from_int8", fu_from_int8, METH_VARARGS, "Pack int8 to byte list."},
    {"from_int32", fu_from_int32, METH_VARARGS, "Pack int32 to byte list."},
    {"from_double", fu_from_double, METH_VARARGS, "Pack double to byte list."},
    {"memcpy", fu_memcpy, METH_VARARGS, "Copy byte items from src to dest list."},
    {nullptr, nullptr, 0, nullptr}
};

static struct PyModuleDef fastutilmodule = {
    PyModuleDef_HEAD_INIT,
    "_fastutil",
    "Fast utility helpers for hbctool.",
    -1,
    FastUtilMethods
};

PyMODINIT_FUNC PyInit__fastutil(void) {
    return PyModule_Create(&fastutilmodule);
}
