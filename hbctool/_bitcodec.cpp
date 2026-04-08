#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>

static int read_u8(PyObject* obj, Py_ssize_t idx, uint8_t* out) {
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

static PyObject* bc_le_to_uint(PyObject*, PyObject* args, PyObject* kwargs) {
    PyObject* buf;
    int signed_flag = 0;
    static const char* kwlist[] = {"buf", "signed", nullptr};
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O|p", (char**)kwlist, &buf, &signed_flag)) {
        return nullptr;
    }

    Py_ssize_t n = PySequence_Size(buf);
    if (n < 0) return nullptr;
    if (n > 8) {
        PyErr_SetString(PyExc_ValueError, "supports up to 8 bytes");
        return nullptr;
    }

    uint64_t u = 0;
    for (Py_ssize_t i = 0; i < n; ++i) {
        uint8_t b;
        if (read_u8(buf, i, &b) != 0) return nullptr;
        u |= ((uint64_t)b) << (i * 8);
    }

    if (signed_flag && n > 0) {
        uint64_t sign_bit = (uint64_t)1 << (n * 8 - 1);
        if (u & sign_bit) {
            int64_t s = (int64_t)(u | (~0ULL << (n * 8)));
            return PyLong_FromLongLong(s);
        }
    }

    return PyLong_FromUnsignedLongLong(u);
}

static PyObject* bc_uint_to_le(PyObject*, PyObject* args, PyObject* kwargs) {
    unsigned long long value;
    int nbytes;
    static const char* kwlist[] = {"value", "nbytes", nullptr};
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "Ki", (char**)kwlist, &value, &nbytes)) {
        return nullptr;
    }

    if (nbytes < 0 || nbytes > 8) {
        PyErr_SetString(PyExc_ValueError, "nbytes must be in [0, 8]");
        return nullptr;
    }

    PyObject* out = PyBytes_FromStringAndSize(nullptr, nbytes);
    if (!out) return nullptr;

    char* raw = PyBytes_AS_STRING(out);
    for (int i = 0; i < nbytes; ++i) {
        raw[i] = (char)((value >> (i * 8)) & 0xFF);
    }

    return out;
}

static PyMethodDef methods[] = {
    {"le_to_uint", (PyCFunction)bc_le_to_uint, METH_VARARGS | METH_KEYWORDS, "Decode little-endian bytes to int."},
    {"uint_to_le", (PyCFunction)bc_uint_to_le, METH_VARARGS | METH_KEYWORDS, "Encode int to little-endian bytes."},
    {nullptr, nullptr, 0, nullptr},
};

static struct PyModuleDef mod = {
    PyModuleDef_HEAD_INIT,
    "_bitcodec",
    "C++ bit/byte codec helpers",
    -1,
    methods,
};

PyMODINIT_FUNC PyInit__bitcodec(void) {
    return PyModule_Create(&mod);
}
