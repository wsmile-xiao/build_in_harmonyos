#!/usr/bin/env python3
"""gengetopt 真实断言：喂一份最小 .ggo，生成 cmdline.c/h，核对生成物内容。

断言三条（都是 gengetopt 的核心契约）：
  ① 退出码为 0 且生成出 cmdline.h / cmdline.c 两个文件
  ② cmdline.h 里有选项对应的结构体成员 `verbose_flag` 与 `name_arg`
  ③ cmdline.c 里有解析入口 `cmdline_parser`
生成不出正确内容 = 这个工具在设备上是废的（lcalc 的 configure 正靠它）。
"""
import os
import subprocess
import sys
import tempfile

GGO = """package "demo"
version "1.0"
option "verbose" v "be verbose" flag off
option "name" n "your name" string required
"""


def main(argv):
    if len(argv) < 2:
        print("用法: test.py <gengetopt 可执行文件>", file=sys.stderr)
        return 2
    exe = argv[1]
    if not os.path.isfile(exe):
        print("[FAIL] 缺可执行文件: %s" % exe)
        return 1
    d = tempfile.mkdtemp()
    ggo = os.path.join(d, "demo.ggo")
    with open(ggo, "w", encoding="utf-8") as f:
        f.write(GGO)
    out = subprocess.run([exe, "--input=" + ggo, "--output-dir=" + d],
                         capture_output=True, text=True, timeout=300)
    if out.returncode != 0:
        print("[FAIL] gengetopt 退出码 %d: %s" % (out.returncode, (out.stderr or "")[-400:]))
        return 1
    h, c = os.path.join(d, "cmdline.h"), os.path.join(d, "cmdline.c")
    if not (os.path.isfile(h) and os.path.isfile(c)):
        print("[FAIL] 没生成 cmdline.h / cmdline.c")
        return 1
    ht = open(h, encoding="utf-8", errors="replace").read()
    ct = open(c, encoding="utf-8", errors="replace").read()
    bad = 0
    for name, text, needle in (("cmdline.h", ht, "verbose_flag"),
                               ("cmdline.h", ht, "name_arg"),
                               ("cmdline.c", ct, "cmdline_parser")):
        if needle not in text:
            print("[FAIL] %s 里没有 %s" % (name, needle))
            bad += 1
        else:
            print("[PASS] %s 含 %s" % (name, needle))
    print("gengetopt: 3 条断言，失败 %d 条" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
