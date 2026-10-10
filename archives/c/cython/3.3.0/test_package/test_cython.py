#!/usr/bin/env python3
"""cython consumer test (R34): the packaged Cython must be a *working*
C-extension compiler, not just an importable directory.

Three independent checks, all on the packaged artefacts:

1. `import Cython` from the package site-packages + version check.
2. **Load a compiled Cython extension module** from the package
   (`Cython.Compiler.Scanning` etc.).  These are foreign ELFs: on OHOS an
   unsigned/mangled `.so` fails `dlopen` (E212), so this check fails if the
   packaging step broke the signature.
3. **Actually use the packaged `cython` CLI** to transpile a real `.pyx`
   to C and verify the output is genuine Cython-generated C (contains the
   CPython API entry point).  This exercises the shipped `bin/cython`
   entry point end to end without needing a C compiler in the test env.
"""
import os
import subprocess
import sys
import tempfile

PYX_SRC = """\
# cython: language_level=3
def add(int a, int b):
    cdef int total = a + b
    return total
"""

CHECK_PY = r'''
import os
import subprocess
import sys
import tempfile

site = os.environ["OHC_CY_SITE"]
pkg_bin = os.environ["OHC_CY_BIN"]
sys.path[0:0] = [site]

# ---- 1) 包内 Cython 可导入 + 版本 ----
import Cython
assert Cython.__version__ == "3.3.0", Cython.__version__
print("Cython", Cython.__version__)

# ---- 2) 加载编译出的扩展模块（E212：签名被打断则在此失败）----
from Cython.Compiler import Scanning          # noqa: F401
from Cython.Plex import Scanners              # noqa: F401
from Cython import _shared                    # noqa: F401
print("compiled extensions load OK (Scanning, Scanners, _shared)")

# ---- 3) 用包内 cython CLI 把真实 .pyx 编译成 C ----
work = tempfile.mkdtemp(prefix="cy-consumer-")
pyx = os.path.join(work, "demo.pyx")
with open(pyx, "w", encoding="utf-8") as f:
    f.write(os.environ["OHC_CY_PYX"])

cli = os.path.join(pkg_bin, "cython")
assert os.path.isfile(cli), "packaged cython CLI missing: %s" % cli
r = subprocess.run([sys.executable, cli, "-3", pyx],
                   cwd=work, capture_output=True, text=True)
if r.returncode != 0:
    raise SystemExit("cython CLI failed rc=%d:\n%s\n%s"
                     % (r.returncode, r.stdout, r.stderr))

gen_c = os.path.join(work, "demo.c")
assert os.path.isfile(gen_c), "cython produced no .c"
size = os.path.getsize(gen_c)
assert size > 10000, "generated C looks too small: %d" % size
with open(gen_c, encoding="utf-8", errors="replace") as f:
    ctext = f.read()
# Cython 生成的 C 必然包含这些标志
for marker in ("PyInit_demo", "PyModuleDef", "CYTHON_"):
    assert marker in ctext, "generated C missing marker %r" % marker
print("cython CLI transpiled demo.pyx -> demo.c (%d bytes, real Cython output)"
      % size)

print("OK: packaged Cython works as a compiler (module + extensions + CLI)")
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    site = os.path.join(pkg, "lib", "python3.12", "site-packages")
    bindir = os.path.join(pkg, "bin")
    if not os.path.isfile(os.path.join(site, "Cython", "__init__.py")):
        print(f"FAIL: Cython package missing under {site}", file=sys.stderr)
        return 1
    cli = os.path.join(bindir, "cython")
    if not os.path.isfile(cli):
        print(f"FAIL: packaged cython CLI missing: {cli}", file=sys.stderr)
        return 1
    env = dict(os.environ)
    env["PYTHONPATH"] = site
    env["OHC_CY_SITE"] = site
    env["OHC_CY_BIN"] = bindir
    env["OHC_CY_PYX"] = PYX_SRC
    py = sys.executable
    with tempfile.TemporaryDirectory(prefix="cy-check-") as td:
        script = os.path.join(td, "check_cython.py")
        with open(script, "w", encoding="utf-8") as f:
            f.write(CHECK_PY)
        r = subprocess.run([py, script], capture_output=True,
                           text=True, env=env, cwd=td)
    if r.returncode != 0:
        print("FAIL: cython consumer check:\n" + r.stdout + r.stderr,
              file=sys.stderr)
        return 1
    print(r.stdout.strip())
    print("OK: Cython module + compiled extensions + CLI all work")
    return 0


if __name__ == "__main__":
    sys.exit(main())
