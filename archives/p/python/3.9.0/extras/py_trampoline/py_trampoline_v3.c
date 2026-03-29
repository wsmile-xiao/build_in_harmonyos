/*
 * py_trampoline_v3.c — Pure C per-slot trampolines (no inline asm)
 *
 * Design:
 *   - 16 slots × multiple signatures = pre-compiled C functions
 *   - No inline asm, no mmap(PROT_EXEC), pure C code in .so
 *   - Each slot has a set of trampoline functions for different signatures
 *   - Thread-safe: each slot has its own functions, no global mutable state
 *   - Python C API calls wrapped in PyGILState_Ensure/Release
 *
 * Compile:
 *   cc -shared -fPIC -I$PREFIX/include/python3.9 \
 *      py_trampoline_v3.c $PREFIX/lib/libpython3.9.so \
 *      -o py_trampoline.so
 */

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>
#include <string.h>
#include <dlfcn.h>

#define MAX_SLOTS 16

typedef struct {
    PyObject *callable;
} SlotEntry;

static SlotEntry slots[MAX_SLOTS];
static int next_slot = 0;

/* =================== Core dispatch =================== */

static int _get_slot(int s) {
    if (s >= 0 && s < MAX_SLOTS && slots[s].callable) return s;
    return -1;
}

static long _call_i1(int s, int64_t a1) {
    PyGILState_STATE g = PyGILState_Ensure();
    long r = 0;
    PyObject *py = PyObject_CallFunction(slots[s].callable, "L", a1);
    if (py) { r = PyLong_AsLong(py); Py_DECREF(py); }
    else PyErr_Print();
    PyGILState_Release(g);
    return r;
}

static long _call_i2(int s, int64_t a1, int64_t a2) {
    PyGILState_STATE g = PyGILState_Ensure();
    long r = 0;
    PyObject *py = PyObject_CallFunction(slots[s].callable, "LL", a1, a2);
    if (py) { r = PyLong_AsLong(py); Py_DECREF(py); }
    else PyErr_Print();
    PyGILState_Release(g);
    return r;
}

static long _call_i5(int s, int64_t a1, int64_t a2, int64_t a3, int64_t a4, int64_t a5) {
    PyGILState_STATE g = PyGILState_Ensure();
    long r = 0;
    PyObject *py = PyObject_CallFunction(slots[s].callable, "LLLLL", a1, a2, a3, a4, a5);
    if (py) { r = PyLong_AsLong(py); Py_DECREF(py); }
    else PyErr_Print();
    PyGILState_Release(g);
    return r;
}

static long _call_i5d(int s, double a1, double a2, double a3, double a4, double a5) {
    PyGILState_STATE g = PyGILState_Ensure();
    long r = 0;
    PyObject *py = PyObject_CallFunction(slots[s].callable, "ddddd", a1, a2, a3, a4, a5);
    if (py) { r = (long)PyFloat_AsDouble(py); Py_DECREF(py); }
    else PyErr_Print();
    PyGILState_Release(g);
    return r;
}

static long _call_d1i(int s, int64_t a1) {
    PyGILState_STATE g = PyGILState_Ensure();
    long r = 0;
    PyObject *py = PyObject_CallFunction(slots[s].callable, "L", a1);
    if (py) { r = (long)PyFloat_AsDouble(py); Py_DECREF(py); }
    else PyErr_Print();
    PyGILState_Release(g);
    return r;
}

static double _call_d1(int s, double a1) {
    PyGILState_STATE g = PyGILState_Ensure();
    double r = 0.0;
    PyObject *py = PyObject_CallFunction(slots[s].callable, "d", a1);
    if (py) { r = PyFloat_AsDouble(py); Py_DECREF(py); }
    else PyErr_Print();
    PyGILState_Release(g);
    return r;
}

static double _call_d5(int s, double a1, double a2, double a3, double a4, double a5) {
    PyGILState_STATE g = PyGILState_Ensure();
    double r = 0.0;
    PyObject *py = PyObject_CallFunction(slots[s].callable, "ddddd", a1, a2, a3, a4, a5);
    if (py) { r = PyFloat_AsDouble(py); Py_DECREF(py); }
    else PyErr_Print();
    PyGILState_Release(g);
    return r;
}

static double _call_d5i(int s, int64_t a1, int64_t a2, int64_t a3, int64_t a4, int64_t a5) {
    PyGILState_STATE g = PyGILState_Ensure();
    double r = 0.0;
    PyObject *py = PyObject_CallFunction(slots[s].callable, "LLLLL", a1, a2, a3, a4, a5);
    if (py) { r = PyFloat_AsDouble(py); Py_DECREF(py); }
    else PyErr_Print();
    PyGILState_Release(g);
    return r;
}

static void _call_v1(int s, int64_t a1) {
    PyGILState_STATE g = PyGILState_Ensure();
    PyObject *py = PyObject_CallFunction(slots[s].callable, "L", a1);
    Py_XDECREF(py);
    if (PyErr_Occurred()) PyErr_Print();
    PyGILState_Release(g);
}

static void _call_v2(int s, int64_t a1, int64_t a2) {
    PyGILState_STATE g = PyGILState_Ensure();
    PyObject *py = PyObject_CallFunction(slots[s].callable, "LL", a1, a2);
    Py_XDECREF(py);
    if (PyErr_Occurred()) PyErr_Print();
    PyGILState_Release(g);
}

static void _call_v1d(int s, double a1) {
    PyGILState_STATE g = PyGILState_Ensure();
    PyObject *py = PyObject_CallFunction(slots[s].callable, "d", a1);
    Py_XDECREF(py);
    if (PyErr_Occurred()) PyErr_Print();
    PyGILState_Release(g);
}

static long _call_i0(int s) {
    PyGILState_STATE g = PyGILState_Ensure();
    long r = 0;
    PyObject *py = PyObject_CallFunction(slots[s].callable, "");
    if (py) { r = PyLong_AsLong(py); Py_DECREF(py); }
    else PyErr_Print();
    PyGILState_Release(g);
    return r;
}

static void _call_v0(int s) {
    PyGILState_STATE g = PyGILState_Ensure();
    PyObject *py = PyObject_CallFunction(slots[s].callable, "");
    Py_XDECREF(py);
    if (PyErr_Occurred()) PyErr_Print();
    PyGILState_Release(g);
}

/* =================== Per-slot trampoline functions =================== */

/* Return int/long: 1 int arg */
#define DEF_II(s) \
int64_t tr_s##s##_ii(int64_t a1) { return _call_i1(s, a1); }
/* Return int/long: 1 double arg */
#define DEF_ID(s) \
int64_t tr_s##s##_id(double a1) { return _call_d1i(s, a1); }
/* Return int/long: 2 int args */
#define DEF_III(s) \
int64_t tr_s##s##_iii(int64_t a1, int64_t a2) { return _call_i2(s, a1, a2); }
/* Return int/long: 5 int args */
#define DEF_IIIII(s) \
int64_t tr_s##s##_iiiii(int64_t a1, int64_t a2, int64_t a3, int64_t a4, int64_t a5) { return _call_i5(s, a1, a2, a3, a4, a5); }
/* Return int/long: 5 double args */
#define DEF_IDDDD(s) \
int64_t tr_s##s##_idddd(double a1, double a2, double a3, double a4, double a5) { return _call_i5d(s, a1, a2, a3, a4, a5); }
/* Return int/long: 0 args */
#define DEF_I0(s) \
int64_t tr_s##s##_i0() { return _call_i0(s); }

/* Return double: 1 int arg */
#define DEF_DI(s) \
double tr_s##s##_di(int64_t a1) { return _call_d1i(s, a1); }
/* Return double: 1 double arg */
#define DEF_DD(s) \
double tr_s##s##_dd(double a1) { return _call_d1(s, a1); }
/* Return double: 5 double args */
#define DEF_DDDDD(s) \
double tr_s##s##_ddddd(double a1, double a2, double a3, double a4, double a5) { return _call_d5(s, a1, a2, a3, a4, a5); }
/* Return double: 5 int args */
#define DEF_DIIII(s) \
double tr_s##s##_diiii(int64_t a1, int64_t a2, int64_t a3, int64_t a4, int64_t a5) { return _call_d5i(s, a1, a2, a3, a4, a5); }

/* Return void: 1 int arg */
#define DEF_VI(s) \
void tr_s##s##_vi(int64_t a1) { _call_v1(s, a1); }
/* Return void: 1 double arg */
#define DEF_VD(s) \
void tr_s##s##_vd(double a1) { _call_v1d(s, a1); }
/* Return void: 2 int args */
#define DEF_VII(s) \
void tr_s##s##_vii(int64_t a1, int64_t a2) { _call_v2(s, a1, a2); }
/* Return void: 0 args */
#define DEF_V0(s) \
void tr_s##s##_v0() { _call_v0(s); }

/* Generate all 16 slots × 14 signatures = 224 functions */
#define GEN_SLOT(s) \
    DEF_II(s) DEF_ID(s) DEF_III(s) DEF_IIIII(s) DEF_IDDDD(s) DEF_I0(s) \
    DEF_DI(s) DEF_DD(s) DEF_DDDDD(s) DEF_DIIII(s) \
    DEF_VI(s) DEF_VD(s) DEF_VII(s) DEF_V0(s)

GEN_SLOT(0)  GEN_SLOT(1)  GEN_SLOT(2)  GEN_SLOT(3)
GEN_SLOT(4)  GEN_SLOT(5)  GEN_SLOT(6)  GEN_SLOT(7)
GEN_SLOT(8)  GEN_SLOT(9)  GEN_SLOT(10) GEN_SLOT(11)
GEN_SLOT(12) GEN_SLOT(13) GEN_SLOT(14) GEN_SLOT(15)

/* =================== Function pointer lookup (no dlsym) =================== */

typedef void (*fn_ptr)(void);

/* Signature index: 0=ii, 1=id, 2=iii, 3=iiiii, 4=idddd, 5=i0, 6=di, 7=dd, 8=ddddd, 9=diiii, 10=vi, 11=vd, 12=vii, 13=v0 */
#define NUM_SIGS 14

static fn_ptr ptr_table[MAX_SLOTS][NUM_SIGS] = {
    { (fn_ptr)tr_s0_ii, (fn_ptr)tr_s0_id, (fn_ptr)tr_s0_iii, (fn_ptr)tr_s0_iiiii, (fn_ptr)tr_s0_idddd, (fn_ptr)tr_s0_i0,
      (fn_ptr)tr_s0_di, (fn_ptr)tr_s0_dd, (fn_ptr)tr_s0_ddddd, (fn_ptr)tr_s0_diiii, (fn_ptr)tr_s0_vi, (fn_ptr)tr_s0_vd, (fn_ptr)tr_s0_vii, (fn_ptr)tr_s0_v0 },
    { (fn_ptr)tr_s1_ii, (fn_ptr)tr_s1_id, (fn_ptr)tr_s1_iii, (fn_ptr)tr_s1_iiiii, (fn_ptr)tr_s1_idddd, (fn_ptr)tr_s1_i0,
      (fn_ptr)tr_s1_di, (fn_ptr)tr_s1_dd, (fn_ptr)tr_s1_ddddd, (fn_ptr)tr_s1_diiii, (fn_ptr)tr_s1_vi, (fn_ptr)tr_s1_vd, (fn_ptr)tr_s1_vii, (fn_ptr)tr_s1_v0 },
    { (fn_ptr)tr_s2_ii, (fn_ptr)tr_s2_id, (fn_ptr)tr_s2_iii, (fn_ptr)tr_s2_iiiii, (fn_ptr)tr_s2_idddd, (fn_ptr)tr_s2_i0,
      (fn_ptr)tr_s2_di, (fn_ptr)tr_s2_dd, (fn_ptr)tr_s2_ddddd, (fn_ptr)tr_s2_diiii, (fn_ptr)tr_s2_vi, (fn_ptr)tr_s2_vd, (fn_ptr)tr_s2_vii, (fn_ptr)tr_s2_v0 },
    { (fn_ptr)tr_s3_ii, (fn_ptr)tr_s3_id, (fn_ptr)tr_s3_iii, (fn_ptr)tr_s3_iiiii, (fn_ptr)tr_s3_idddd, (fn_ptr)tr_s3_i0,
      (fn_ptr)tr_s3_di, (fn_ptr)tr_s3_dd, (fn_ptr)tr_s3_ddddd, (fn_ptr)tr_s3_diiii, (fn_ptr)tr_s3_vi, (fn_ptr)tr_s3_vd, (fn_ptr)tr_s3_vii, (fn_ptr)tr_s3_v0 },
    { (fn_ptr)tr_s4_ii, (fn_ptr)tr_s4_id, (fn_ptr)tr_s4_iii, (fn_ptr)tr_s4_iiiii, (fn_ptr)tr_s4_idddd, (fn_ptr)tr_s4_i0,
      (fn_ptr)tr_s4_di, (fn_ptr)tr_s4_dd, (fn_ptr)tr_s4_ddddd, (fn_ptr)tr_s4_diiii, (fn_ptr)tr_s4_vi, (fn_ptr)tr_s4_vd, (fn_ptr)tr_s4_vii, (fn_ptr)tr_s4_v0 },
    { (fn_ptr)tr_s5_ii, (fn_ptr)tr_s5_id, (fn_ptr)tr_s5_iii, (fn_ptr)tr_s5_iiiii, (fn_ptr)tr_s5_idddd, (fn_ptr)tr_s5_i0,
      (fn_ptr)tr_s5_di, (fn_ptr)tr_s5_dd, (fn_ptr)tr_s5_ddddd, (fn_ptr)tr_s5_diiii, (fn_ptr)tr_s5_vi, (fn_ptr)tr_s5_vd, (fn_ptr)tr_s5_vii, (fn_ptr)tr_s5_v0 },
    { (fn_ptr)tr_s6_ii, (fn_ptr)tr_s6_id, (fn_ptr)tr_s6_iii, (fn_ptr)tr_s6_iiiii, (fn_ptr)tr_s6_idddd, (fn_ptr)tr_s6_i0,
      (fn_ptr)tr_s6_di, (fn_ptr)tr_s6_dd, (fn_ptr)tr_s6_ddddd, (fn_ptr)tr_s6_diiii, (fn_ptr)tr_s6_vi, (fn_ptr)tr_s6_vd, (fn_ptr)tr_s6_vii, (fn_ptr)tr_s6_v0 },
    { (fn_ptr)tr_s7_ii, (fn_ptr)tr_s7_id, (fn_ptr)tr_s7_iii, (fn_ptr)tr_s7_iiiii, (fn_ptr)tr_s7_idddd, (fn_ptr)tr_s7_i0,
      (fn_ptr)tr_s7_di, (fn_ptr)tr_s7_dd, (fn_ptr)tr_s7_ddddd, (fn_ptr)tr_s7_diiii, (fn_ptr)tr_s7_vi, (fn_ptr)tr_s7_vd, (fn_ptr)tr_s7_vii, (fn_ptr)tr_s7_v0 },
    { (fn_ptr)tr_s8_ii, (fn_ptr)tr_s8_id, (fn_ptr)tr_s8_iii, (fn_ptr)tr_s8_iiiii, (fn_ptr)tr_s8_idddd, (fn_ptr)tr_s8_i0,
      (fn_ptr)tr_s8_di, (fn_ptr)tr_s8_dd, (fn_ptr)tr_s8_ddddd, (fn_ptr)tr_s8_diiii, (fn_ptr)tr_s8_vi, (fn_ptr)tr_s8_vd, (fn_ptr)tr_s8_vii, (fn_ptr)tr_s8_v0 },
    { (fn_ptr)tr_s9_ii, (fn_ptr)tr_s9_id, (fn_ptr)tr_s9_iii, (fn_ptr)tr_s9_iiiii, (fn_ptr)tr_s9_idddd, (fn_ptr)tr_s9_i0,
      (fn_ptr)tr_s9_di, (fn_ptr)tr_s9_dd, (fn_ptr)tr_s9_ddddd, (fn_ptr)tr_s9_diiii, (fn_ptr)tr_s9_vi, (fn_ptr)tr_s9_vd, (fn_ptr)tr_s9_vii, (fn_ptr)tr_s9_v0 },
    { (fn_ptr)tr_s10_ii, (fn_ptr)tr_s10_id, (fn_ptr)tr_s10_iii, (fn_ptr)tr_s10_iiiii, (fn_ptr)tr_s10_idddd, (fn_ptr)tr_s10_i0,
      (fn_ptr)tr_s10_di, (fn_ptr)tr_s10_dd, (fn_ptr)tr_s10_ddddd, (fn_ptr)tr_s10_diiii, (fn_ptr)tr_s10_vi, (fn_ptr)tr_s10_vd, (fn_ptr)tr_s10_vii, (fn_ptr)tr_s10_v0 },
    { (fn_ptr)tr_s11_ii, (fn_ptr)tr_s11_id, (fn_ptr)tr_s11_iii, (fn_ptr)tr_s11_iiiii, (fn_ptr)tr_s11_idddd, (fn_ptr)tr_s11_i0,
      (fn_ptr)tr_s11_di, (fn_ptr)tr_s11_dd, (fn_ptr)tr_s11_ddddd, (fn_ptr)tr_s11_diiii, (fn_ptr)tr_s11_vi, (fn_ptr)tr_s11_vd, (fn_ptr)tr_s11_vii, (fn_ptr)tr_s11_v0 },
    { (fn_ptr)tr_s12_ii, (fn_ptr)tr_s12_id, (fn_ptr)tr_s12_iii, (fn_ptr)tr_s12_iiiii, (fn_ptr)tr_s12_idddd, (fn_ptr)tr_s12_i0,
      (fn_ptr)tr_s12_di, (fn_ptr)tr_s12_dd, (fn_ptr)tr_s12_ddddd, (fn_ptr)tr_s12_diiii, (fn_ptr)tr_s12_vi, (fn_ptr)tr_s12_vd, (fn_ptr)tr_s12_vii, (fn_ptr)tr_s12_v0 },
    { (fn_ptr)tr_s13_ii, (fn_ptr)tr_s13_id, (fn_ptr)tr_s13_iii, (fn_ptr)tr_s13_iiiii, (fn_ptr)tr_s13_idddd, (fn_ptr)tr_s13_i0,
      (fn_ptr)tr_s13_di, (fn_ptr)tr_s13_dd, (fn_ptr)tr_s13_ddddd, (fn_ptr)tr_s13_diiii, (fn_ptr)tr_s13_vi, (fn_ptr)tr_s13_vd, (fn_ptr)tr_s13_vii, (fn_ptr)tr_s13_v0 },
    { (fn_ptr)tr_s14_ii, (fn_ptr)tr_s14_id, (fn_ptr)tr_s14_iii, (fn_ptr)tr_s14_iiiii, (fn_ptr)tr_s14_idddd, (fn_ptr)tr_s14_i0,
      (fn_ptr)tr_s14_di, (fn_ptr)tr_s14_dd, (fn_ptr)tr_s14_ddddd, (fn_ptr)tr_s14_diiii, (fn_ptr)tr_s14_vi, (fn_ptr)tr_s14_vd, (fn_ptr)tr_s14_vii, (fn_ptr)tr_s14_v0 },
    { (fn_ptr)tr_s15_ii, (fn_ptr)tr_s15_id, (fn_ptr)tr_s15_iii, (fn_ptr)tr_s15_iiiii, (fn_ptr)tr_s15_idddd, (fn_ptr)tr_s15_i0,
      (fn_ptr)tr_s15_di, (fn_ptr)tr_s15_dd, (fn_ptr)tr_s15_ddddd, (fn_ptr)tr_s15_diiii, (fn_ptr)tr_s15_vi, (fn_ptr)tr_s15_vd, (fn_ptr)tr_s15_vii, (fn_ptr)tr_s15_v0 },
};

static int _sig_index(const char *sig) {
    if (!strcmp(sig, "ii")) return 0;
    if (!strcmp(sig, "id")) return 1;
    if (!strcmp(sig, "iii")) return 2;
    if (!strcmp(sig, "iiiii")) return 3;
    if (!strcmp(sig, "idddd")) return 4;
    if (!strcmp(sig, "i0")) return 5;
    if (!strcmp(sig, "di")) return 6;
    if (!strcmp(sig, "dd")) return 7;
    if (!strcmp(sig, "ddddd")) return 8;
    if (!strcmp(sig, "diiii")) return 9;
    if (!strcmp(sig, "vi")) return 10;
    if (!strcmp(sig, "vd")) return 11;
    if (!strcmp(sig, "vii")) return 12;
    if (!strcmp(sig, "v0")) return 13;
    return -1;
}

/* =================== Python module =================== */

PyObject* py_alloc_slot(PyObject *self, PyObject *args) {
    (void)self;
    int s = next_slot++;
    if (s >= MAX_SLOTS) { PyErr_SetString(PyExc_RuntimeError, "No slots"); return NULL; }
    return PyLong_FromLong(s);
}

PyObject* py_register(PyObject *self, PyObject *args) {
    (void)self;
    int slot; PyObject *cb;
    if (!PyArg_ParseTuple(args, "iO", &slot, &cb)) return NULL;
    if (slot < 0 || slot >= MAX_SLOTS) { PyErr_SetString(PyExc_ValueError, "bad slot"); return NULL; }
    Py_XDECREF(slots[slot].callable);
    memset(&slots[slot], 0, sizeof(SlotEntry));
    slots[slot].callable = cb;
    Py_INCREF(cb);
    Py_RETURN_NONE;
}

PyObject* py_unregister(PyObject *self, PyObject *args) {
    (void)self;
    int slot;
    if (!PyArg_ParseTuple(args, "i", &slot)) return NULL;
    if (slot >= 0 && slot < MAX_SLOTS) {
        Py_XDECREF(slots[slot].callable);
        memset(&slots[slot], 0, sizeof(SlotEntry));
    }
    Py_RETURN_NONE;
}

PyObject* py_get_trampoline_ptr(PyObject *self, PyObject *args) {
    (void)self;
    int slot; const char *sig;
    if (!PyArg_ParseTuple(args, "is", &slot, &sig)) return NULL;
    int idx = _sig_index(sig);
    if (idx < 0 || slot < 0 || slot >= MAX_SLOTS) {
        PyErr_Format(PyExc_ValueError, "Unknown sig %s for slot %d", sig, slot);
        return NULL;
    }
    return PyLong_FromVoidPtr(ptr_table[slot][idx]);
}

static PyMethodDef module_methods[] = {
    {"alloc_slot", py_alloc_slot, METH_NOARGS, "Allocate a callback slot (0-15)"},
    {"register", py_register, METH_VARARGS, "register(slot, callable)"},
    {"unregister", py_unregister, METH_VARARGS, "unregister(slot)"},
    {"get_trampoline_ptr", py_get_trampoline_ptr, METH_VARARGS,
     "get_trampoline_ptr(slot, sig)\n"
     "  sig: 'ii','id','iii','iiiii','idddd','i0'\n"
     "       'dd','di','ddddd','diiii'\n"
     "       'vi','vd','vii','v0'"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT, "py_trampoline",
    "Pure C callback trampolines for HarmonyOS (W^X workaround)",
    -1, module_methods
};

PyMODINIT_FUNC PyInit_py_trampoline(void) {
    memset(slots, 0, sizeof(slots));
    return PyModule_Create(&moduledef);
}
