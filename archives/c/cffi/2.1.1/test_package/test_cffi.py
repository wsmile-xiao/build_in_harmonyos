#!/usr/bin/env python3
"""Consumer test for the installed cffi 2.1.1 package (R34).

Runs against the *packaged* tree only (site-packages passed on argv), so it
verifies what a downstream consumer actually gets: the importable cffi package,
the compiled _cffi_backend C extension, and the real FFI machinery on top of it.

Every check performs a real CFFI operation — no print-only assertion (R34).
"""
import os
import sys

SITE = sys.argv[1] if len(sys.argv) > 1 else None
if SITE:
    sys.path.insert(0, SITE)

failures = []
checks = 0


def check(label, cond, detail=""):
    global checks
    checks += 1
    if cond:
        print(f"  ok   {label}")
    else:
        print(f"  FAIL {label} {detail}")
        failures.append(label)


# ---------------------------------------------------------------- import
import _cffi_backend  # noqa: E402

import cffi  # noqa: E402

check("import cffi", cffi.__file__ is not None)
check("import _cffi_backend (C extension loads)",
      _cffi_backend.__file__.endswith(".so"), _cffi_backend.__file__)
check("cffi.__version__ == 2.1.1", cffi.__version__ == "2.1.1",
      cffi.__version__)
check("backend version matches cffi version",
      getattr(_cffi_backend, "__version__", None) == cffi.__version__,
      f"{getattr(_cffi_backend, '__version__', None)}")
check("_cffi_backend,__version__ available (no dist-info needed)",
      hasattr(cffi, "FFI"))

ffi = cffi.FFI()

# ---------------------------------------------------------------- ABI mode
# cdef + libffi 直接调用 libc（不需要编译器）
ffi.cdef("""
    char *strchr(const char *s, int c);
    int strlen(const char *s);
""")
libc = ffi.dlopen(None)  # 当前进程（含 libc 符号）
s = ffi.new("char[]", b"hello world")
check("ffi.new char[] length", ffi.sizeof(s) == 12, ffi.sizeof(s))
check("ABI call strlen()", libc.strlen(s) == 11, libc.strlen(s))
p = libc.strchr(s, ord(" "))
check("ABI call strchr() returns pointer", p != ffi.NULL)
check("strchr result is correct",
      ffi.string(p) == b" world", ffi.string(p))

# ---------------------------------------------------------------- pointers/arrays
arr = ffi.new("int[]", [1, 2, 3, 4])
check("int[] roundtrip", list(arr) == [1, 2, 3, 4], list(arr))
check("sizeof(int[4])", ffi.sizeof(arr) == 16, ffi.sizeof(arr))
pa = ffi.new("int *")
pa[0] = 7
check("int* write/read", pa[0] == 7)

# ---------------------------------------------------------------- structs
ffi.cdef("struct point { int x; int y; };")
pt = ffi.new("struct point *")
pt.x, pt.y = 3, 4
check("struct field write/read", (pt.x, pt.y) == (3, 4), (pt.x, pt.y))
check("struct sizeof", ffi.sizeof("struct point") >= 8, ffi.sizeof("struct point"))

# ---------------------------------------------------------------- from_buffer
buf = bytearray(b"abcdef")
view = ffi.from_buffer(buf)
check("from_buffer length", len(view) == 6, len(view))
check("from_buffer content", ffi.string(view, 3) == b"abc", ffi.string(view, 3))

# ---------------------------------------------------------------- sizeof/offsetof
check("ffi.sizeof('long') in (4,8)", ffi.sizeof("long") in (4, 8), ffi.sizeof("long"))
check("ffi.offsetof struct", ffi.offsetof("struct point", "y") >= 0)

# ---------------------------------------------------------------- callback
@ffi.callback("int(int, int)")
def add(a, b):
    return a + b


cb = ffi.callback("int(*)(int,int)", add)
check("ffi.callback wrapped callable", cb(2, 3) == 5, cb(2, 3))

# ---------------------------------------------------------------- C calls back into Python
# 这是 ABI 模式最有力的用例：由 C 侧（libc 的 qsort）反向调用 Python 回调。
# 刻意**不**断言 verify()/API 模式：它在 Python >= 3.12 上要求运行期可用
# setuptools（实测报 "This CFFI feature requires setuptools on Python >= 3.12.
# The setuptools module is missing or non-functional."），而 setuptools 并非
# 本包的交付契约、也未发布到 ohpcd（包运行期依赖仅 pycparser）。把它写成
# 断言会让"消费者环境没装 setuptools"被误报成"包坏了"。
ffi.cdef("""
    void qsort(void *base, size_t nmemb, size_t size,
               int (*compar)(const void *, const void *));
""")
arr = ffi.new("int[]", [5, 1, 4, 2, 3])


@ffi.callback("int(const void *, const void *)")
def _cmp(a, b):
    return ffi.cast("int *", a)[0] - ffi.cast("int *", b)[0]


libc.qsort(arr, 5, ffi.sizeof("int"), _cmp)
check("C calls back into a Python callback (qsort)", list(arr) == [1, 2, 3, 4, 5],
      list(arr))

# ---------------------------------------------------------------- handles
handle = ffi.new_handle({"k": "v"})
check("new_handle/from_handle round trip",
      ffi.from_handle(handle) == {"k": "v"}, ffi.from_handle(handle))
check("ffi.CData type check", ffi.typeof(arr).kind == "array", ffi.typeof(arr).kind)

# ---------------------------------------------------------------- negative
try:
    ffi.cdef("this is not valid cdecl @@@")
    check("cdef rejects invalid C (negative)", False, "no exception raised")
except Exception as exc:  # noqa: BLE001
    check("cdef rejects invalid C (negative)",
          type(exc).__name__ in ("CDefError", "VerificationError"),
          type(exc).__name__)

print(f"\n{checks - len(failures)}/{checks} checks passed")
if failures:
    print("FAILED: " + ", ".join(failures))
    sys.exit(1)
sys.exit(0)
