#!/usr/bin/env python3
"""test_package 驱动 — lfortran 0.64.0 消费者视角验证。

用法（conan test_package 调用，env=conanrun 注入 LD_LIBRARY_PATH）：
    python3 test_lfortran.py <package-folder>

真实调用编译器二进制（R34），四组探针：
  1. --backend=llvm 编译 test_lfortran.f90 → 运行产物 → 断言 stdout 含 ALL_OK 且退出码 0
  2. --backend=c 编译（0.64.0 c 后端自带 gcc 驱动编译+链接产出二进制，编译器名经
     LFORTRAN_GCC 环境变量注入——包配方 runenv_info 提供）→ 运行 → 断言 ALL_OK
  3. --show-llvm 输出非空且含 "define"（LLVM IR 检视路径）
  4. --version 输出含版本号
全部通过则退出 0，否则退出非 0。

注意：OHOS /tmp 只读（HMDFS），产物目录用 $HOME 下 mkdtemp。
"""
import os
import subprocess
import sys
import tempfile


def run(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)


def main():
    pkg = sys.argv[1]
    lfortran = os.path.join(pkg, "bin", "lfortran")
    if not os.path.isfile(lfortran):
        print("FAIL: lfortran binary missing under {}/bin".format(pkg))
        return 1
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_lfortran.f90")
    work = tempfile.mkdtemp(prefix="lfortran-tp-", dir=os.environ.get("HOME", "."))
    fails = []

    diag = "PATH={} LFORTRAN_CC={!r} LFORTRAN_GCC={!r} LFORTRAN_LINKER={!r}".format(
        os.environ.get("PATH", "")[:400],
        os.environ.get("LFORTRAN_CC"), os.environ.get("LFORTRAN_GCC"),
        os.environ.get("LFORTRAN_LINKER"))

    # 1. LLVM 后端：编译 → 运行
    exe = os.path.join(work, "prog_llvm")
    r = run('"{}" --backend=llvm "{}" -o "{}"'.format(lfortran, src, exe))
    if r.returncode != 0 or not os.path.isfile(exe):
        fails.append("llvm backend compile failed: {} | {}".format(r.stderr[-600:], diag))
    else:
        r2 = run('"{}"'.format(exe))
        if r2.returncode != 0 or "ALL_OK" not in r2.stdout:
            fails.append("llvm backend run failed: rc={} out={!r} err={!r}".format(
                r2.returncode, r2.stdout[:200], r2.stderr[-300:]))

    # 2. C 后端：0.64.0 的 --backend=c 由 lfortran 自身驱动 gcc 完成
    #    C 生成 → 编译 → 链接（产出二进制）；编译器名经 LFORTRAN_GCC 注入。
    cexe = os.path.join(work, "prog_c")
    r = run('"{}" --backend=c "{}" -o "{}"'.format(lfortran, src, cexe))
    if r.returncode != 0 or not os.path.isfile(cexe):
        fails.append("c backend compile failed: {} | {}".format(r.stderr[-600:], diag))
    else:
        r2 = run('"{}"'.format(cexe))
        if r2.returncode != 0 or "ALL_OK" not in r2.stdout:
            fails.append("c backend run failed: rc={} out={!r} err={!r}".format(
                r2.returncode, r2.stdout[:200], r2.stderr[-300:]))

    # 3. --show-llvm 中间表示检视
    r = run('"{}" --show-llvm "{}"'.format(lfortran, src))
    if r.returncode != 0 or "define" not in r.stdout:
        fails.append("show-llvm failed: rc={} out={!r}".format(r.returncode, r.stdout[:200]))

    # 4. --version
    r = run('"{}" --version'.format(lfortran))
    if r.returncode != 0 or "0.64.0" not in r.stdout + r.stderr:
        fails.append("version check failed: rc={} out={!r}".format(r.returncode, (r.stdout + r.stderr)[:200]))

    if fails:
        print("FAIL: {} probe(s) failed:".format(len(fails)))
        for f in fails:
            print("  - " + f)
        return 1
    print("PASS: lfortran consumer probes (llvm/c backends, show-llvm, version)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
