#!/usr/bin/env python3
"""test_sdcc.py — consumer test source for sdcc 4.6.0 (L0c).

REAL API check (R34): compile a minimal 8051 C program with the packaged
sdcc (--std-c11 -mmcs51) and assert the Intel HEX output (.ihx) is produced.
Usage: test_sdcc.py <package-folder>

HMDFS lesson: the conan package lives on /storage (HMDFS), where
posix_spawn of the packaged binaries fails with "Operation not
permitted" (same class as the perl .so Permission denied). Copy the
whole package to a non-HMDFS partition (/data) and run sdcc from there —
verified working: the /data work tree's bin/sdcc compiles device libs.
"""
import os
import shutil
import subprocess
import sys
import tempfile


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_sdcc.py <package-folder>")
    pkg = sys.argv[1]
    sdcc = os.path.join(pkg, "bin", "sdcc")
    if not os.path.isfile(sdcc):
        raise AssertionError(f"sdcc binary missing: {sdcc}")
    # 候选非 HMDFS 根：/data/storage/el2/base/cache 与 /data/cache 是
    # 非 HMDFS（chmod/执行正常，手动验证 8051 编译成功）；TMPDIR
    # （本机 =/storage，HMDFS）必须放最后——HMDFS 上 sdcc 无法正常
    # 编译输出（ihx 缺失），且执行可能被拒。
    roots = ["/data/storage/el2/base/cache", "/data/cache",
             os.environ.get("TMPDIR"), tempfile.gettempdir()]
    work_root = None
    for r in roots:
        if not r or not os.path.isdir(r):
            continue
        try:
            probe = os.path.join(r, ".sdcc-t-probe")
            with open(probe, "w") as _f:
                _f.write("x")
            os.remove(probe)
            work_root = r
            break
        except OSError:
            continue
    if not work_root:
        raise AssertionError("no writable non-hmdfs root for sdcc test")
    work = tempfile.mkdtemp(prefix="sdcc-t-", dir=work_root)
    try:
        # 复制整个包（bin+share+lib+libexec 保持相对结构，SDCC 驱动
        # 基于 argv[0] 相对定位 cc1 与设备库）
        for entry in ("bin", "share", "lib", "libexec"):
            s = os.path.join(pkg, entry)
            if os.path.isdir(s):
                shutil.copytree(s, os.path.join(work, entry))
        # sdcpp（gcc cpp）找 cc1 用 STANDARD_LIBEXEC_PREFIX 编译宏——
        # 指向构建时 install-prefix 的绝对路径，复制到 /data 新目录后
        # 该路径失效（CI 清理后报 "cannot execute 'cc1'"）。把 cc1 复制
        # 到 bin/（sdcpp 同目录）并设 PATH，gcc cpp 通过 PATH 找到 cc1
        # （已实测：原 install-prefix 移走后，bin/cc1 + PATH 编译成功）。
        cc1_src = None
        for root, _dirs, files in os.walk(os.path.join(work, "libexec")):
            if "cc1" in files:
                cc1_src = os.path.join(root, "cc1")
                break
        if cc1_src:
            cc1_dst = os.path.join(work, "bin", "cc1")
            shutil.copy2(cc1_src, cc1_dst)
            os.chmod(cc1_dst, 0o777)
        w_sdcc = os.path.join(work, "bin", "sdcc")
        if not os.path.isfile(w_sdcc):
            raise AssertionError(f"sdcc missing in work copy: {w_sdcc}")
        for root, _dirs, files in os.walk(work):
            for f in files:
                p = os.path.join(root, f)
                if os.access(p, os.X_OK) and os.path.isfile(p):
                    try:
                        os.chmod(p, 0o777)
                    except OSError:
                        pass
        # minimal 8051 C program (blink-free, plain loop — compiles anywhere)
        src = ("/* minimal 8051 target program */\n"
               "void main(void) { volatile unsigned char i; "
               "for (i = 0; i < 10; i++) ; }\n")
        c_file = os.path.join(work, "t8051.c")
        with open(c_file, "w") as f:
            f.write(src)
        r = subprocess.run([w_sdcc, "--std-c11", "-mmcs51", c_file],
                           capture_output=True, text=True,
                           cwd=work,  # sdcc 把 .ihx/.rel 等输出到当前目录——
                           # 必须 cwd=work，否则 .ihx 落在进程 cwd 而非 work
                           env=dict(os.environ, PATH=os.path.join(work, "bin") + os.pathsep + os.environ.get("PATH", "")))
        if r.returncode != 0:
            sys.stderr.write(r.stderr or "")
            raise SystemExit(f"sdcc compile failed (rc={r.returncode})")
        ihx = os.path.join(work, "t8051.ihx")
        if not os.path.isfile(ihx):
            raise AssertionError(f"sdcc output .ihx missing: {ihx}")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print("OK: sdcc 4.6.0 real API ok (8051 compile -> .ihx)")


if __name__ == "__main__":
    main()
