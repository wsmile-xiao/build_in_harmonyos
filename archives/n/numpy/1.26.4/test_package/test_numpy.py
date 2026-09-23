#!/usr/bin/env python3
"""numpy consumer test (L0c + R34): standalone test source executed
via self.run from conanfile.py test().

R34: actually call the tested API — numpy.array() + arithmetic on real
arrays (C-extension core, pure user-space computation). Import failure or
wrong result asserts fail.

Diagnostics (2026-09-10): never swallow the underlying ImportError. NumPy's
"you should not try to import numpy from its source directory" text is only a
wrapper message; we print the full traceback, the chained cause, and the raw
loader error for numpy.core._multiarray_umath, plus which libpython is
actually mapped, so the first real failure is visible in the CI log.
"""
import os
import sys
import traceback


def _mapped_libpython() -> str:
    try:
        with open("/proc/self/maps", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if "libpython3" in line:
                    return line.rstrip()
    except OSError:
        pass
    return "(libpython3 not found in /proc/self/maps)"


def _dump_env() -> None:
    print("---- numpy test diagnostics ----", file=sys.stderr)
    print(f"executable : {sys.executable}", file=sys.stderr)
    print(f"version    : {sys.version.splitlines()[0]}", file=sys.stderr)
    print(f"prefix     : {sys.prefix}", file=sys.stderr)
    print(f"base_prefix: {sys.base_prefix}", file=sys.stderr)
    print(f"cwd        : {os.getcwd()}", file=sys.stderr)
    print(f"sys.path   : {sys.path}", file=sys.stderr)
    print(f"LD_LIBRARY_PATH: {os.environ.get('LD_LIBRARY_PATH','')}", file=sys.stderr)
    print(f"PYTHONPATH     : {os.environ.get('PYTHONPATH','')}", file=sys.stderr)
    print(f"mapped libpython: {_mapped_libpython()}", file=sys.stderr)
    print("--------------------------------", file=sys.stderr)


def _inspect_ext() -> None:
    """Show why the C-extension would/would not load on this target."""
    import glob
    import stat as _stat
    hits = []
    for base in sys.path:
        if not base:
            continue
        hits = glob.glob(os.path.join(base, "numpy", "core",
                                      "_multiarray_umath*.so"))
        if hits:
            break
    if not hits:
        print("---- ext inspect: _multiarray_umath*.so not found in sys.path "
              f"({sys.path}) ----", file=sys.stderr)
        return
    p = hits[0]
    st = os.stat(p)
    print("---- ext inspect ----", file=sys.stderr)
    print(f"path : {p}", file=sys.stderr)
    print(f"mode : {_stat.filemode(st.st_mode)} ({oct(st.st_mode & 0o7777)})",
          file=sys.stderr)
    print(f"uid  : {st.st_uid} gid: {st.st_gid} "
          f"(this proc uid={os.getuid()} gid={os.getgid()})", file=sys.stderr)
    print(f"access R_OK={os.access(p, os.R_OK)} X_OK={os.access(p, os.X_OK)}",
          file=sys.stderr)
    try:
        with open(p, "rb") as fh:
            blob = fh.read()
        print(f"size : {len(blob)}", file=sys.stderr)
        print(f"has .note.ohos.ident marker: {b'.note.ohos.ident' in blob}",
              file=sys.stderr)
        print(f"has .codesign marker       : {b'.codesign' in blob}",
              file=sys.stderr)
    except OSError as e:
        print(f"read failed: {type(e).__name__}: {e}", file=sys.stderr)
    try:
        import ctypes
        ctypes.CDLL(p)
        print("ctypes.CDLL: loaded OK", file=sys.stderr)
    except OSError as e:
        print(f"ctypes.CDLL failed: {type(e).__name__}: {e}", file=sys.stderr)
    # Ancestor directory permissions: traversal denial also yields EACCES.
    d = os.path.dirname(p)
    for _ in range(8):
        if d in ("", "/"):
            break
        try:
            dst = os.stat(d)
            print(f"dir  : {_stat.filemode(dst.st_mode)} "
                  f"({oct(dst.st_mode & 0o7777)}) uid={dst.st_uid} "
                  f"gid={dst.st_gid} X_OK={os.access(d, os.X_OK)} {d}",
                  file=sys.stderr)
        except OSError as e:
            print(f"dir  : stat failed {d}: {e}", file=sys.stderr)
        d = os.path.dirname(d)
    print("--------------------", file=sys.stderr)


def main() -> int:
    _dump_env()
    _inspect_ext()

    # Raw C-extension loader error first (bypasses numpy/__init__.py wrapper).
    try:
        import numpy.core._multiarray_umath  # noqa: F401
        print("OK: numpy.core._multiarray_umath imported", file=sys.stderr)
    except BaseException:
        print("FAIL: raw import of numpy.core._multiarray_umath raised:",
              file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

    try:
        import numpy as np
    except ImportError as e:
        print(f"FAIL: cannot import numpy: {e}", file=sys.stderr)
        cause = e.__cause__
        depth = 1
        while cause is not None and depth < 6:
            print(f"FAIL: chained cause ({depth}): {type(cause).__name__}: "
                  f"{cause}", file=sys.stderr)
            cause = cause.__cause__
            depth += 1
        traceback.print_exc(file=sys.stderr)
        return 1

    # 真实调用 API：array 构造 + 运算（C 扩展核心）
    try:
        a = np.array([1, 2, 3])
        b = a * 2
    except Exception as e:
        print(f"FAIL: np.array() raised: {e}", file=sys.stderr)
        return 1

    if not hasattr(b, "tolist"):
        print(f"FAIL: np.array()*2 returned {type(b)!r} (expected ndarray)",
              file=sys.stderr)
        return 1
    if b.tolist() != [2, 4, 6]:
        print(f"FAIL: array([1,2,3])*2={b.tolist()!r} (expected [2,4,6])",
              file=sys.stderr)
        return 1

    # dtype 与形状（C 扩展元数据）
    if b.dtype is None or b.shape != (3,):
        print(f"FAIL: array shape/dtype unexpected: {b.shape}/{b.dtype}",
              file=sys.stderr)
        return 1

    print(f"OK: numpy {np.__version__} real API ok "
          f"(array([1,2,3])*2={b.tolist()!r})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
