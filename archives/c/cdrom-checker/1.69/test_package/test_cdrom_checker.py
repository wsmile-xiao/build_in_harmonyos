#!/usr/bin/env python3
"""cdrom-checker 1.69 consumer test — C application verification.

Checks the installed package: bin/cdrom-checker exists, is non-empty, is
executable, is an ELF binary, and its DT_NEEDED entries really reference
libdebconfclient.so.0 and libdebian-installer.so.4 (proving the build-time
link against cdebconf/libdebian-installer actually resolved — not a static
fake artifact). Exits non-zero on any failure.
"""
import os
import subprocess
import sys

BIN = os.path.join("bin", "cdrom-checker")
NEEDED = ("libdebconfclient.so.0", "libdebian-installer.so.4")


def smoke_run(exe, cdebconf_root):
    """P3 加固：真实执行包内二进制，断言链接依赖可解析且 debconf
    链路可用（区分源码构建产物与手工塞入的预编译二进制）。
    MENU 非空且 != argv[0] → return-to-menu 路径，无 /cdrom 时 rc=0。"""
    import tempfile

    work = tempfile.mkdtemp(prefix="cdrom-checker-smoke-")
    conf = os.path.join(work, "cdebconf.conf")
    with open(conf, "w", encoding="utf-8") as f:
        f.write(
            "global {\n"
            "  module_path {\n"
            '    frontend "%s";\n'
            '    database "%s";\n'
            "  };\n"
            "  default {\n"
            '    frontend "default_fe";\n'
            '    template "templatedb";\n'
            '    config "configdb";\n'
            "  };\n"
            "};\n"
            'frontend { instance "default_fe" { driver "passthrough"; } };\n'
            'template { instance "templatedb" { driver "rfc822db"; path "%s"; } };\n'
            'config { instance "configdb" { driver "textdb"; path "%s"; } };\n'
            % (os.path.join(cdebconf_root, "libexec", "cdebconf", "frontend"),
               os.path.join(cdebconf_root, "libexec", "cdebconf", "db"),
               os.path.join(work, "templates.dat"),
               os.path.join(work, "questions.dat"))
        )
    env = dict(os.environ)
    env["MENU"] = "cdrom-checker"
    env["DEBCONF_PATH"] = conf
    env["LD_LIBRARY_PATH"] = os.pathsep.join(
        [os.path.join(cdebconf_root, "libexec", "cdebconf"),
         os.path.join(cdebconf_root, "lib")])
    try:
        # stdin=DEVNULL: the debconf passthrough frontend's INPUT reads the
        # terminal; a non-EOF stdin hangs forever (observed on the CI worker).
        r = subprocess.run([exe], stdin=subprocess.DEVNULL,
                           capture_output=True, env=env, timeout=30)
    except Exception as e:  # noqa: BLE001
        print("[FAIL] smoke run error: %s" % e)
        return 1
    out = (r.stdout or b"").decode(errors="replace")
    err = (r.stderr or b"").decode(errors="replace")
    if r.returncode != 0:
        print("[FAIL] smoke run rc=%d (expected 0): %s"
              % (r.returncode, err.strip()[:200]))
        return 1
    print("[ok] smoke run rc=0 (binary executed, link deps resolved)")
    if "GET cdrom-checker/start" not in out:
        print("[FAIL] smoke output missing debconf set/input/go/get "
              "interaction")
        return 1
    print("[ok] debconf set/input/go/get interaction observed")
    return 0


def main():
    pkg_root = sys.argv[1] if len(sys.argv) > 1 else "."
    cdebconf_root = sys.argv[2] if len(sys.argv) > 2 else None
    failures = 0

    exe = os.path.join(pkg_root, BIN)
    if not os.path.isfile(exe):
        print("[FAIL] %s missing" % exe)
        return 1
    if os.path.getsize(exe) == 0:
        print("[FAIL] %s empty" % BIN)
        failures += 1
    else:
        print("[ok] %s present (%d bytes)" % (BIN, os.path.getsize(exe)))
    if not os.access(exe, os.X_OK):
        print("[FAIL] %s not executable" % BIN)
        failures += 1
    else:
        print("[ok] %s executable" % BIN)
    with open(exe, "rb") as f:
        magic = f.read(4)
    if magic != b"\x7fELF":
        print("[FAIL] %s is not an ELF binary (magic=%r)" % (BIN, magic))
        failures += 1
    else:
        print("[ok] %s is ELF" % BIN)
    # DT_NEEDED: prefer the OHOS toolchain readelf, fall back to any readelf.
    # A missing candidate raises FileNotFoundError (OSError); catch it so the
    # fallback to PATH actually runs instead of the probe dying with a
    # traceback on the first absent path.
    readelf = None
    for cand in ("/data/service/hnp/bin/readelf", "readelf"):
        try:
            r = subprocess.run([cand, "--version"], capture_output=True)
        except OSError:
            continue
        if r.returncode == 0:
            readelf = cand
            break
    if not readelf:
        print("[FAIL] readelf unavailable, cannot verify DT_NEEDED")
        return 1
    r = subprocess.run([readelf, "-d", exe], capture_output=True)
    if r.returncode != 0:
        print("[FAIL] readelf -d %s failed: %s"
              % (BIN, r.stderr.decode(errors="replace").strip()))
        return 1
    dyn = (r.stdout or b"").decode(errors="replace")
    for lib in NEEDED:
        if lib in dyn:
            print("[ok] DT_NEEDED contains %s" % lib)
        else:
            print("[FAIL] DT_NEEDED missing %s" % lib)
            failures += 1

    # P3 加固：真实执行包内二进制（2 项断言），需要 cdebconf 包根提供
    # debconf 前端/数据库模块与库文件；缺省时跳过（CI 环境恒提供）。
    if cdebconf_root:
        failures += smoke_run(exe, cdebconf_root)
    else:
        print("[skip] smoke run (cdebconf package root not provided)")

    if failures:
        print("cdrom-checker: %d assertion(s) failed" % failures)
        return 1
    print("cdrom-checker package OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
