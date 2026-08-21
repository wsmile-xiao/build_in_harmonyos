#!/usr/bin/env python3
"""gbdk-2020 consumer test (R34): compile a minimal Game Boy ROM.

Runs the packaged lcc (gbdk compiler driver) + SDCC toolchain to build a
tiny .gb ROM from C — proving the packaged toolchain (lcc → sdcc →
sdasgb/sdldgb) is actually usable on OHOS (real API check).
"""
import os
import shutil
import subprocess
import sys


def main():
    if len(sys.argv) != 2:
        print("usage: test_gbdk.py <package-folder>")
        return 1
    pkg = sys.argv[1]
    bindir = os.path.join(pkg, "bin")
    if not os.path.isfile(os.path.join(bindir, "lcc")):
        raise AssertionError(f"gbdk lcc missing: {bindir}/lcc")
    # HMDFS execution limit: conan cache lives under /storage (hmdfs),
    # posix_spawn of packaged bins fails with EPERM ("Operation not
    # permitted") — same as sdcc test. Copy the toolchain to a non-hmdfs
    # dir (/data candidates) before running lcc.
    work_root = None
    for cand in ("/data/storage/el2/base/cache", "/data/cache"):
        try:
            os.makedirs(cand, exist_ok=True)
            probe = os.path.join(cand, ".gbdk-w-probe")
            with open(probe, "w") as _f:
                _f.write("x")
            os.remove(probe)
            work_root = cand
            break
        except OSError:
            continue
    if not work_root:
        raise AssertionError("no writable non-hmdfs dir for gbdk test")
    work = os.path.join(work_root, f"gbdk-test-{os.getpid()}")
    # copy the whole package (bin+include+lib+libexec): lcc derives
    # prefix from argv[0] (set_gbdk_dir strips GBDKDIR/bin/lcc → prefix),
    # then resolves %prefix%include (gb/gb.h), %prefix%lib/, and sdcc
    # bins from %prefix%bin/ — so the package layout must be preserved
    for entry in ("bin", "include", "lib", "libexec"):
        s = os.path.join(pkg, entry)
        if os.path.isdir(s):
            shutil.copytree(s, os.path.join(work, entry), dirs_exist_ok=True)
    # sdcpp finds cc1 via its STANDARD_LIBEXEC_PREFIX compile macro
    # (build-time install-prefix, dead after copy) — sdcc same fix:
    # put cc1 next to sdcpp in bin/ so PATH lookup succeeds
    cc1_src = None
    for root, _dirs, files in os.walk(os.path.join(work, "libexec")):
        if "cc1" in files:
            cc1_src = os.path.join(root, "cc1")
            break
    if cc1_src:
        cc1_dst = os.path.join(work, "bin", "cc1")
        shutil.copy2(cc1_src, cc1_dst)
        os.chmod(cc1_dst, 0o777)
    for root, _dirs, files in os.walk(work):
        for f in files:
            p = os.path.join(root, f)
            if os.access(p, os.X_OK):
                try:
                    os.chmod(p, 0o777)
                except OSError:
                    pass
    lcc = os.path.join(work, "bin", "lcc")
    src = os.path.join(work, "main.c")
    with open(src, "w") as f:
        f.write("#include <gb/gb.h>\n"
                "void main(void) {\n"
                "    SPRITES_8x8;\n"
                "    SHOW_BKG;\n"
                "    while (1) { vsync(); }\n"
                "}\n")
    env = dict(os.environ)
    env["PATH"] = os.path.join(work, "bin") + os.pathsep + env.get("PATH", "")
    r = subprocess.run([lcc, "-o", os.path.join(work, "main.gb"), src],
                       capture_output=True, text=True, env=env, cwd=work)
    if r.stdout:
        sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr or "")
        raise AssertionError(f"gbdk lcc compile failed (rc={r.returncode})")
    gb = os.path.join(work, "main.gb")
    if not os.path.isfile(gb) or os.path.getsize(gb) == 0:
        raise AssertionError(f"no .gb ROM produced: {gb}")
    print(f"OK: gbdk-2020 4.5.0 real API ok "
          f"(lcc -> .gb ROM, {os.path.getsize(gb)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
