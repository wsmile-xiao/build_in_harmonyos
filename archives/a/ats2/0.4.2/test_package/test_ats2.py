#!/usr/bin/env python3
"""ats2-postiats consumer test (L0c + R34): standalone test source
executed via self.run from conanfile.py test().

R34: actually invoke the tested compiler — patscc compiles a minimal
ATS program to a runnable binary, then execute it.

Usage: test_ats2.sh <bindir> <patshome>
"""
import os
import shutil
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <bindir> <patshome>", file=sys.stderr)
        return 2
    bindir, patshome = sys.argv[1], sys.argv[2]
    patscc = os.path.join(bindir, "patscc")
    if not os.path.isfile(patscc):
        raise AssertionError(f"patscc missing in {bindir}")
    # R34: 用 patscc 编译一个最小 ATS 程序并运行
    # 源码/产物/工作目录全部放在无空格路径（工作目录可能含空格/括号
    # ——patscc 内部 sh 命令解析失败实测：syntax error: unexpected '('
    # ——同 autodocksuite 教训——CI 目录无空格但本地验证需兼容）
    src_orig = os.path.join(os.path.dirname(__file__), "hello_ats.dats")
    workdir = "/data/storage/el2/base/cache/ats2-tp-test"
    os.makedirs(workdir, exist_ok=True)
    src = os.path.join(workdir, "hello_ats.dats")
    shutil.copyfile(src_orig, src)
    exe = os.path.join(workdir, "hello_ats")
    env = dict(os.environ)
    env["PATSHOME"] = patshome
    # OHOS 无 gcc——patscc 内部调用 gcc 编译生成的 C 代码（实测
    # 'sh: gcc: inaccessible or not found'）——注入 gcc→clang 软链 PATH
    binlink = "/data/storage/el2/base/cache/ats2-tp-bin"
    os.makedirs(binlink, exist_ok=True)
    for ln, tgt in (("gcc", "/data/service/hnp/bin/clang"),
                    ("g++", "/data/service/hnp/bin/clang++")):
        p = os.path.join(binlink, ln)
        if not os.path.exists(p):
            os.symlink(tgt, p)
    # patscc 内部靠 PATH 查找 patsopt（打包目录无 bin/patsopt——
    # 实测 'patscc failed' 空 stderr）——把预编译工具链 bin 加入 PATH
    toolbin = "/data/storage/el2/base/cache/ats2-build/bin"
    env["PATH"] = (f"{binlink}:{toolbin}:"
                   f"{env.get('PATH', '')}")
    cmd = [patscc, "-o", exe, src, "-DATS_MEMALLOC_LIBC", "-latslib"]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True,
                       timeout=120, cwd=workdir)
    if r.returncode != 0:
        raise AssertionError(f"patscc failed: {r.stderr[:500]}")
    r2 = subprocess.run([exe], env=env, capture_output=True, text=True,
                        timeout=30)
    if r2.returncode != 0:
        raise AssertionError(f"compiled program failed: {r2.stderr[:300]}")
    if "hello" not in r2.stdout.lower():
        raise AssertionError(f"unexpected output: {r2.stdout[:200]}")
    print(f"OK: ats2 0.4.2 (patscc compile+run: {r2.stdout.strip()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
