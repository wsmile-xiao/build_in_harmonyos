/*
 * py_trampoline.c — Pre-compiled C trampolines for ctypes callbacks on HarmonyOS
 *
 * HarmonyOS kernel enforces W^X: mmap(PROT_EXEC) always fails.
 * libffi's ffi_closure_alloc() needs executable memory → MemoryError.
 *
 * Solution: all trampoline code lives in this .so's text segment (file-backed r-xp),
 * which is allowed.  Slot management replaces ffi_closure allocation.
 *
 * Design:
 *   - MAX_SLOTS (32) independent callback slots
 *   - Each slot stores: callable, converters, setfunc, ffi_restype, flags
 *   - Pre-compiled trampolines for common signatures (0-6 args, int/double types)
 *   - Pointer args reuse int trampolines (same ABI on aarch64)
 *   - Three core dispatchers: _tramp_ret_int, _tramp_ret_double, _tramp_ret_void
 *     that call _CallPythonObject() from callbacks.c
 */

#include "Python.h"
#include <ffi.h>
#include "ctypes.h"
#include <stdint.h>
#include <string.h>

/* =================== Configuration =================== */

#define MAX_SLOTS 128
#define MAX_ARGS  6

/* =================== Slot data =================== */

typedef struct {
    PyObject *callable;     /* Python callback function */
    PyObject *converters;   /* argument converter tuple */
    SETFUNC    setfunc;     /* result conversion function */
    ffi_type  *ffi_restype; /* result ffi_type */
    int        flags;       /* FUNCFLAG_* */
    Py_ssize_t nArgs;       /* argument count */
    int        active;      /* slot in use */
} SlotData;

static SlotData g_slots[MAX_SLOTS];
static int g_next_slot = 0;

/* =================== _CallPythonObject is defined in callbacks.c =================== */

extern void _CallPythonObject(void *mem, ffi_type *restype, SETFUNC setfunc,
                              PyObject *callable, PyObject *converters,
                              int flags, void **pArgs);

/* =================== Core dispatchers =================== */

static int64_t _tramp_ret_int(int slot, void **args)
{
    SlotData *sd = &g_slots[slot];
    if (!sd->active || !sd->callable) return 0;

    ffi_arg resp = 0;
    _CallPythonObject(&resp, sd->ffi_restype, sd->setfunc,
                      sd->callable, sd->converters, sd->flags, args);
    return (int64_t)resp;
}

static double _tramp_ret_double(int slot, void **args)
{
    SlotData *sd = &g_slots[slot];
    if (!sd->active || !sd->callable) return 0.0;

    ffi_arg resp = 0;
    _CallPythonObject(&resp, sd->ffi_restype, sd->setfunc,
                      sd->callable, sd->converters, sd->flags, args);
    /* resp is ffi_arg (8 bytes), setfunc wrote the double value into it */
    double result;
    memcpy(&result, &resp, sizeof(double));
    return result;
}

static void _tramp_ret_void(int slot, void **args)
{
    SlotData *sd = &g_slots[slot];
    if (!sd->active || !sd->callable) return;

    _CallPythonObject(NULL, sd->ffi_restype, NULL,
                      sd->callable, sd->converters, sd->flags, args);
}

/* =================== Parameter macros for 0..6 args =================== */
/* I = int64_t (integer/pointer args), D = double (float args) */

/* --- int64_t parameters --- */
#define P_I0  void
#define P_I1  int64_t a1
#define P_I2  int64_t a1, int64_t a2
#define P_I3  int64_t a1, int64_t a2, int64_t a3
#define P_I4  int64_t a1, int64_t a2, int64_t a3, int64_t a4
#define P_I5  int64_t a1, int64_t a2, int64_t a3, int64_t a4, int64_t a5
#define P_I6  int64_t a1, int64_t a2, int64_t a3, int64_t a4, int64_t a5, int64_t a6

#define A_I0  /* nothing */
#define A_I1  &a1
#define A_I2  &a1, &a2
#define A_I3  &a1, &a2, &a3
#define A_I4  &a1, &a2, &a3, &a4
#define A_I5  &a1, &a2, &a3, &a4, &a5
#define A_I6  &a1, &a2, &a3, &a4, &a5, &a6

/* --- double parameters --- */
#define P_D0  void
#define P_D1  double a1
#define P_D2  double a1, double a2
#define P_D3  double a1, double a2, double a3
#define P_D4  double a1, double a2, double a3, double a4
#define P_D5  double a1, double a2, double a3, double a4, double a5
#define P_D6  double a1, double a2, double a3, double a4, double a5, double a6

#define A_D0  NULL   /* 0 args: dummy entry, _CallPythonObject won't read it */
#define A_D1  &a1
#define A_D2  &a1, &a2
#define A_D3  &a1, &a2, &a3
#define A_D4  &a1, &a2, &a3, &a4
#define A_D5  &a1, &a2, &a3, &a4, &a5
#define A_D6  &a1, &a2, &a3, &a4, &a5, &a6

/* =================== Trampoline function generators =================== */

/* Return int, N int args */
#define TR_I_IN(s, n) \
    int64_t tr_##s##_i_I##n(P_I##n) { \
        void *_a[] = { A_I##n }; \
        return _tramp_ret_int(s, _a); \
    }

/* Return int, N double args */
#define TR_I_DN(s, n) \
    int64_t tr_##s##_i_D##n(P_D##n) { \
        void *_a[] = { A_D##n }; \
        return _tramp_ret_int(s, _a); \
    }

/* Return double, N int args */
#define TR_D_IN(s, n) \
    double tr_##s##_d_I##n(P_I##n) { \
        void *_a[] = { A_I##n }; \
        return _tramp_ret_double(s, _a); \
    }

/* Return double, N double args */
#define TR_D_DN(s, n) \
    double tr_##s##_d_D##n(P_D##n) { \
        void *_a[] = { A_D##n }; \
        return _tramp_ret_double(s, _a); \
    }

/* Return void, N int args */
#define TR_V_IN(s, n) \
    void tr_##s##_v_I##n(P_I##n) { \
        void *_a[] = { A_I##n }; \
        _tramp_ret_void(s, _a); \
    }

/* Return void, N double args */
#define TR_V_DN(s, n) \
    void tr_##s##_v_D##n(P_D##n) { \
        void *_a[] = { A_D##n }; \
        _tramp_ret_void(s, _a); \
    }

/* =================== Mixed-type trampolines =================== */
/* Some ctypes tests use CFUNCTYPE(c_double, c_byte, c_double) etc.
 * These have mixed int+double params. We generate the specific
 * mixed signatures needed rather than all 2^n combinations. */

/* Return int, params (int, double) */
#define TR_I_ID(s) \
    int64_t tr_##s##_i_ID(int64_t a1, double a2) { \
        void *_a[] = {&a1, &a2}; \
        return _tramp_ret_int(s, _a); \
    }
/* Return int, params (double, int) */
#define TR_I_DI(s) \
    int64_t tr_##s##_i_DI(double a1, int64_t a2) { \
        void *_a[] = {&a1, &a2}; \
        return _tramp_ret_int(s, _a); \
    }
/* Return double, params (int, double) */
#define TR_D_ID(s) \
    double tr_##s##_d_ID(int64_t a1, double a2) { \
        void *_a[] = {&a1, &a2}; \
        return _tramp_ret_double(s, _a); \
    }
/* Return double, params (double, int) */
#define TR_D_DI(s) \
    double tr_##s##_d_DI(double a1, int64_t a2) { \
        void *_a[] = {&a1, &a2}; \
        return _tramp_ret_double(s, _a); \
    }
/* Return double, params (int, int, double) */
#define TR_D_IID(s) \
    double tr_##s##_d_IID(int64_t a1, int64_t a2, double a3) { \
        void *_a[] = {&a1, &a2, &a3}; \
        return _tramp_ret_double(s, _a); \
    }
/* Return void, params (int, double) */
#define TR_V_ID(s) \
    void tr_##s##_v_ID(int64_t a1, double a2) { \
        void *_a[] = {&a1, &a2}; \
        _tramp_ret_void(s, _a); \
    }
/* Return void, params (double, int) */
#define TR_V_DI(s) \
    void tr_##s##_v_DI(double a1, int64_t a2) { \
        void *_a[] = {&a1, &a2}; \
        _tramp_ret_void(s, _a); \
    }

/* =================== Generate all slot functions =================== */

#define GEN_SLOT_RET_I(s) \
    TR_I_IN(s,0) TR_I_IN(s,1) TR_I_IN(s,2) TR_I_IN(s,3) TR_I_IN(s,4) TR_I_IN(s,5) TR_I_IN(s,6) \
    TR_I_DN(s,1) TR_I_DN(s,2) TR_I_DN(s,3) TR_I_DN(s,4) TR_I_DN(s,5) TR_I_DN(s,6) \
    TR_I_ID(s) TR_I_DI(s)

#define GEN_SLOT_RET_D(s) \
    TR_D_IN(s,0) TR_D_IN(s,1) TR_D_IN(s,2) TR_D_IN(s,3) TR_D_IN(s,4) TR_D_IN(s,5) TR_D_IN(s,6) \
    TR_D_DN(s,0) TR_D_DN(s,1) TR_D_DN(s,2) TR_D_DN(s,3) TR_D_DN(s,4) TR_D_DN(s,5) TR_D_DN(s,6) \
    TR_D_ID(s) TR_D_DI(s) TR_D_IID(s)

#define GEN_SLOT_RET_V(s) \
    TR_V_IN(s,0) TR_V_IN(s,1) TR_V_IN(s,2) TR_V_IN(s,3) TR_V_IN(s,4) TR_V_IN(s,5) TR_V_IN(s,6) \
    TR_V_DN(s,0) TR_V_DN(s,1) TR_V_DN(s,2) TR_V_DN(s,3) TR_V_DN(s,4) TR_V_DN(s,5) TR_V_DN(s,6) \
    TR_V_ID(s) TR_V_DI(s)

#define GEN_SLOT(s) \
    GEN_SLOT_RET_I(s) \
    GEN_SLOT_RET_D(s) \
    GEN_SLOT_RET_V(s)

/* Generate 32 slots × 13+7+7+7+7+7 = ~48 signatures = ~1536 functions */
GEN_SLOT(0)  GEN_SLOT(1)  GEN_SLOT(2)  GEN_SLOT(3)
GEN_SLOT(4)  GEN_SLOT(5)  GEN_SLOT(6)  GEN_SLOT(7)
GEN_SLOT(8)  GEN_SLOT(9)  GEN_SLOT(10) GEN_SLOT(11)
GEN_SLOT(12) GEN_SLOT(13) GEN_SLOT(14) GEN_SLOT(15)
GEN_SLOT(16) GEN_SLOT(17) GEN_SLOT(18) GEN_SLOT(19)
GEN_SLOT(20) GEN_SLOT(21) GEN_SLOT(22) GEN_SLOT(23)
GEN_SLOT(24) GEN_SLOT(25) GEN_SLOT(26) GEN_SLOT(27)
GEN_SLOT(28) GEN_SLOT(29) GEN_SLOT(30) GEN_SLOT(31)

/* =================== Signature table =================== */

/*
 * Signature encoding — index into g_ptr_table[slot]:
 *
 *   Row 0:  i_I0  i_I1  i_I2  i_I3  i_I4  i_I5  i_I6  i_D1  i_D2  i_D3  i_D4  i_D5  i_D6  i_ID  i_DI
 *   Row 1:  d_I0  d_I1  d_I2  d_I3  d_I4  d_I5  d_I6  d_D0  d_D1  d_D2  d_D3  d_D4  d_D5  d_D6  d_ID  d_DI  d_IID
 *   Row 2:  v_I0  v_I1  v_I2  v_I3  v_I4  v_I5  v_I6  v_D0  v_D1  v_D2  v_D3  v_D4  v_D5  v_D6  v_ID  v_DI
 */

#define NUM_SIGS 48

typedef void (*fn_ptr)(void);

#define PTR_I_ID(s)  (fn_ptr)tr_##s##_i_ID
#define PTR_I_DI(s)  (fn_ptr)tr_##s##_i_DI
#define PTR_D_ID(s)  (fn_ptr)tr_##s##_d_ID
#define PTR_D_DI(s)  (fn_ptr)tr_##s##_d_DI
#define PTR_D_IID(s) (fn_ptr)tr_##s##_d_IID
#define PTR_V_ID(s)  (fn_ptr)tr_##s##_v_ID
#define PTR_V_DI(s)  (fn_ptr)tr_##s##_v_DI

#define SLOT_PTRS(s) \
    PTR_I_IN(s,0), PTR_I_IN(s,1), PTR_I_IN(s,2), PTR_I_IN(s,3), \
    PTR_I_IN(s,4), PTR_I_IN(s,5), PTR_I_IN(s,6), \
    PTR_I_DN(s,1), PTR_I_DN(s,2), PTR_I_DN(s,3), \
    PTR_I_DN(s,4), PTR_I_DN(s,5), PTR_I_DN(s,6), \
    PTR_I_ID(s), PTR_I_DI(s), \
    PTR_D_IN(s,0), PTR_D_IN(s,1), PTR_D_IN(s,2), PTR_D_IN(s,3), \
    PTR_D_IN(s,4), PTR_D_IN(s,5), PTR_D_IN(s,6), \
    PTR_D_DN(s,0), PTR_D_DN(s,1), PTR_D_DN(s,2), PTR_D_DN(s,3), \
    PTR_D_DN(s,4), PTR_D_DN(s,5), PTR_D_DN(s,6), \
    PTR_D_ID(s), PTR_D_DI(s), PTR_D_IID(s), \
    PTR_V_IN(s,0), PTR_V_IN(s,1), PTR_V_IN(s,2), PTR_V_IN(s,3), \
    PTR_V_IN(s,4), PTR_V_IN(s,5), PTR_V_IN(s,6), \
    PTR_V_DN(s,0), PTR_V_DN(s,1), PTR_V_DN(s,2), PTR_V_DN(s,3), \
    PTR_V_DN(s,4), PTR_V_DN(s,5), PTR_V_DN(s,6), \
    PTR_V_ID(s), PTR_V_DI(s)

static fn_ptr g_ptr_table[MAX_SLOTS][NUM_SIGS] = {
    { SLOT_PTRS(0) },
    { SLOT_PTRS(1) },
    { SLOT_PTRS(2) },
    { SLOT_PTRS(3) },
    { SLOT_PTRS(4) },
    { SLOT_PTRS(5) },
    { SLOT_PTRS(6) },
    { SLOT_PTRS(7) },
    { SLOT_PTRS(8) },
    { SLOT_PTRS(9) },
    { SLOT_PTRS(10) },
    { SLOT_PTRS(11) },
    { SLOT_PTRS(12) },
    { SLOT_PTRS(13) },
    { SLOT_PTRS(14) },
    { SLOT_PTRS(15) },
    { SLOT_PTRS(16) },
    { SLOT_PTRS(17) },
    { SLOT_PTRS(18) },
    { SLOT_PTRS(19) },
    { SLOT_PTRS(20) },
    { SLOT_PTRS(21) },
    { SLOT_PTRS(22) },
    { SLOT_PTRS(23) },
    { SLOT_PTRS(24) },
    { SLOT_PTRS(25) },
    { SLOT_PTRS(26) },
    { SLOT_PTRS(27) },
    { SLOT_PTRS(28) },
    { SLOT_PTRS(29) },
    { SLOT_PTRS(30) },
    { SLOT_PTRS(31) },
};

/* =================== Signature matching =================== */

/*
 * Classify an ffi_type for trampoline selection.
 * On aarch64 AAPCS64: integer/pointer types go in x0-x7, floats in d0-d7.
 */
static char _classify_type(ffi_type *t)
{
    switch (t->type) {
    case FFI_TYPE_UINT8:
    case FFI_TYPE_SINT8:
    case FFI_TYPE_UINT16:
    case FFI_TYPE_SINT16:
    case FFI_TYPE_UINT32:
    case FFI_TYPE_SINT32:
    case FFI_TYPE_UINT64:
    case FFI_TYPE_SINT64:
    case FFI_TYPE_POINTER:
        return 'I';
    case FFI_TYPE_FLOAT:
    case FFI_TYPE_DOUBLE:
        return 'D';
    case FFI_TYPE_LONGDOUBLE:
        /* long double is 16 bytes on aarch64, passed differently.
         * For now, fall through to error. */
        return 'L';
    case FFI_TYPE_STRUCT:
        /* On aarch64, structs > 16 bytes are passed by reference (pointer in xN).
         * Treat as integer/pointer parameter. */
        if (t->size > 16) return 'I';
        /* Small structs passed in registers — not yet supported generically */
        return 'S';
    default:
        return '?';
    }
}

/*
 * Build a signature string and look up the corresponding trampoline.
 *
 * Index layout:
 *   [0..6]   = i_I0..i_I6  (return int, 0-6 int args)
 *   [7..12]  = i_D1..i_D6  (return int, 1-6 double args)
 *   [13]     = i_ID  (return int, 2 args: int, double)
 *   [14]     = i_DI  (return int, 2 args: double, int)
 *   [15..21] = d_I0..d_I6  (return double, 0-6 int args)
 *   [22..28] = d_D0..d_D6  (return double, 0-6 double args)
 *   [29]     = d_ID  (return double, 2 args: int, double)
 *   [30]     = d_DI  (return double, 2 args: double, int)
 *   [31]     = d_IID (return double, 3 args: int, int, double)
 *   [32..38] = v_I0..v_I6  (return void, 0-6 int args)
 *   [39..45] = v_D0..v_D6  (return void, 0-6 double args)
 *   [46]     = v_ID  (return void, 2 args: int, double)
 *   [47]     = v_DI  (return void, 2 args: double, int)
 */
static int _sig_index_for(char ret_type, Py_ssize_t nArgs, ffi_type **atypes)
{
    int base;

    if (nArgs > MAX_ARGS) return -1;

    switch (ret_type) {
    case 'i': base = 0; break;
    case 'd': base = 15; break;
    case 'v': base = 32; break;
    default: return -1;
    }

    if (nArgs == 0) {
        return base;  /* i_I0=0, d_I0=15, v_I0=32 */
    }

    /* Classify all args */
    char types[MAX_ARGS + 1];
    int has_int = 0, has_dbl = 0;
    for (Py_ssize_t i = 0; i < nArgs; i++) {
        types[i] = _classify_type(atypes[i]);
        if (types[i] == 'I') has_int = 1;
        else if (types[i] == 'D') has_dbl = 1;
        else return -1;  /* unsupported type (struct, longdouble, etc.) */
    }
    types[nArgs] = '\0';

    /* All same type — use the existing slots */
    if (!has_dbl) {
        /* All int params: offset = nArgs */
        return base + (int)nArgs;
    }
    if (!has_int) {
        /* All double params */
        return base + 7 + (int)nArgs;
    }

    /* Mixed types — only support specific patterns */
    if (nArgs == 2 && strcmp(types, "ID") == 0) return base + 13; /* _ID */
    if (nArgs == 2 && strcmp(types, "DI") == 0) return base + 14; /* _DI */
    if (nArgs == 3 && ret_type == 'd' && strcmp(types, "IID") == 0) return base + 16; /* d_IID */

    return -1;  /* unsupported mixed pattern */
}

/* =================== Public API for callbacks.c =================== */

/*
 * Allocate a trampoline slot. Returns slot index (>=0) or -1 on failure.
 */
int py_trampoline_alloc_slot(void)
{
    /* Try to find a free slot first (in case some were freed) */
    for (int i = 0; i < MAX_SLOTS; i++) {
        if (!g_slots[i].active) {
            g_next_slot = i + 1;
            return i;
        }
    }
    if (g_next_slot < MAX_SLOTS) {
        return g_next_slot++;
    }
    /* All slots in use — trigger GC and try again */
    PyGC_Collect();
    for (int i = 0; i < MAX_SLOTS; i++) {
        if (!g_slots[i].active) {
            g_next_slot = i + 1;
            return i;
        }
    }
    return -1;
}

/*
 * Register callback data into a slot.
 */
void py_trampoline_register(int slot, PyObject *callable, PyObject *converters,
                            SETFUNC setfunc, ffi_type *ffi_restype, int flags,
                            Py_ssize_t nArgs)
{
    if (slot < 0 || slot >= MAX_SLOTS) return;

    SlotData *sd = &g_slots[slot];
    Py_XDECREF(sd->callable);
    Py_XDECREF(sd->converters);
    memset(sd, 0, sizeof(SlotData));

    sd->callable = callable;
    sd->converters = converters;
    sd->setfunc = setfunc;
    sd->ffi_restype = ffi_restype;
    sd->flags = flags;
    sd->nArgs = nArgs;
    sd->active = 1;

    Py_XINCREF(callable);
    Py_XINCREF(converters);
}

/*
 * Free a trampoline slot.
 */
void py_trampoline_free_slot(int slot)
{
    if (slot < 0 || slot >= MAX_SLOTS) return;

    SlotData *sd = &g_slots[slot];
    Py_XDECREF(sd->callable);
    Py_XDECREF(sd->converters);
    memset(sd, 0, sizeof(SlotData));
}

/*
 * Find the trampoline function pointer for a given signature.
 * Returns the function pointer, or NULL if signature not supported.
 */
void *py_trampoline_find(int slot, ffi_type **atypes, ffi_type *ffi_restype,
                         Py_ssize_t nArgs)
{
    if (slot < 0 || slot >= MAX_SLOTS) return NULL;

    /* Determine return type classification */
    char ret_type;
    if (ffi_restype->type == FFI_TYPE_VOID) {
        ret_type = 'v';
    } else if (ffi_restype->type == FFI_TYPE_FLOAT || ffi_restype->type == FFI_TYPE_DOUBLE) {
        ret_type = 'd';
    } else if (ffi_restype->type == FFI_TYPE_LONGDOUBLE) {
        return NULL;  /* Not supported yet */
    } else {
        ret_type = 'i';  /* All integer/pointer types */
    }

    int idx = _sig_index_for(ret_type, nArgs, atypes);
    if (idx < 0 || idx >= NUM_SIGS) return NULL;

    return (void *)g_ptr_table[slot][idx];
}
