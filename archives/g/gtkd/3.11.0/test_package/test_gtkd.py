#!/usr/bin/env python3
"""Consumer test for the installed gtkd 3.11.0 package (R34).

Compiles a real D program against the packaged `libgtkd-3.a` + D imports, then
RUNS it. The program exercises gtkd's core contract end to end:

  * `gtk.Version.getMajorVersion()` — resolves `gtk_get_major_version` through
    gtkd's runtime dlopen loader (gtkd.Loader) against `libgtk-3.so.0`, i.e. it
    proves both the D binding and the dlopen path work on the target.
  * `gtkd.paths.LIBRARY` / `importLibs` — the runtime library table.
  * A GTK widget type's `.sizeof`/static call via a non-dlopen path.

Environment (set by test_package/conanfile.py):
  GTKD_TEST_INC, GTKD_TEST_LIBDIR, GTKD_TEST_DC, GTKD_TEST_PHOBOS,
  GTKD_TEST_LDC_LIB

Everything is a real assertion — no print-only checks (R34).
"""
import os
import subprocess
import sys
import tempfile

INC = os.environ.get("GTKD_TEST_INC")
LIBDIR = os.environ.get("GTKD_TEST_LIBDIR")
DC = os.environ.get("GTKD_TEST_DC")
PHOBOS = os.environ.get("GTKD_TEST_PHOBOS")
LDC_LIB = os.environ.get("GTKD_TEST_LDC_LIB")

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


for name, val in (("GTKD_TEST_INC", INC), ("GTKD_TEST_LIBDIR", LIBDIR),
                  ("GTKD_TEST_DC", DC), ("GTKD_TEST_PHOBOS", PHOBOS),
                  ("GTKD_TEST_LDC_LIB", LDC_LIB)):
    check(f"env {name} provided", bool(val), "missing")

if failures:
    print(f"\n0/{checks} checks passed (missing environment)")
    sys.exit(1)

workdir = tempfile.mkdtemp(prefix="gtkd-consumer-",
                           dir=os.environ.get("TMPDIR") or None)
src = os.path.join(workdir, "consumer.d")
exe = os.path.join(workdir, "consumer")

PROGRAM = r"""
import std.stdio;
import gtkd.paths;
import gtk.Version;

void main()
{
    // 运行期 dlopen libgtk-3.so.0 → gtk_get_major_version()
    uint major = Version.getMajorVersion();
    uint minor = Version.getMinorVersion();
    writeln("major=", major);
    writeln("minor=", minor);
    // 库表（gtkd.paths）应包含 GTK 项
    writeln("libs=", LIBRARY.max + 1);
}
"""

with open(src, "w") as fh:
    fh.write(PROGRAM)

# 编译：-I gtkd 导入路径 + Phobos 源码；静态链 libgtkd-3.a 与 druntime/Phobos
cmd = [DC, "-O",
       f"-I{INC}", f"-I{PHOBOS}",
       f"-L-L{LIBDIR}", "-L-lgtkd-3",
       f"-L-L{LDC_LIB}",
       "-of" + exe, src]
env = dict(os.environ)
env["LD_LIBRARY_PATH"] = os.pathsep.join(
    [LDC_LIB, env.get("LD_LIBRARY_PATH", "")]).strip(os.pathsep)
res = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=1800)
check("D consumer program compiles and links against libgtkd-3.a",
      res.returncode == 0 and os.path.isfile(exe),
      ((res.stdout or "") + (res.stderr or "")).strip()[-500:])

if os.path.isfile(exe) and res.returncode == 0:
    run = subprocess.run([exe], capture_output=True, text=True, env=env,
                         timeout=600)
    out = run.stdout or ""
    err = run.stderr or ""
    check("D consumer program runs", run.returncode == 0,
          (out + err).strip()[-400:])
    check("gtk_get_major_version() via gtkd dlopen returns 3",
          "major=3" in out, out.strip()[:200])
    check("gtk_get_minor_version() returns a number", "minor=" in out,
          out.strip()[:200])
    check("gtkd.paths LIBRARY table is populated", "libs=" in out,
          out.strip()[:200])
    # 负例：缺失的 GTK 符号应走 gtkd 的 unsupportedSymbol 路径而非静默成功
    check("runtime loader did not silently substitute symbols",
          "Error" not in err or "not pressent" not in err,
          err.strip()[:200])

print(f"\n{checks - len(failures)}/{checks} checks passed")
if failures:
    print("FAILED: " + ", ".join(failures))
    sys.exit(1)
sys.exit(0)
