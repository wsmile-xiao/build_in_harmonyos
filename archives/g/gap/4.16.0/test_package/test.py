#!/usr/bin/env python3
"""GAP 真实计算断言（独立可跑：`python3 test.py <conan 包根>`）。

三条都可手算/查表：
  ① Size(SymmetricGroup(5)) = 120          —— 5! ，最基本的群阶
  ② Size(SmallGroup(8,3)) = 8              —— 顺带证明 smallgrp 包**真的装上了**
  ③ NrPrimitiveGroups(8) = 7               —— 证明 primgrp 包装上了

②③ 是关键：`make install` 一个 GAP 包都不装，缺包时 GAP 照样能起来、
一用到就报 package not available。只跑 ① 会漏掉这类静默功能缺失。
"""
import os
import subprocess
import sys


def run_gap(gap_bin, gap_root, code):
    cmd = [gap_bin, "-l", gap_root, "-q", "-b", "-A", "-c",
           'Print(%s, "\\n"); QUIT;' % code]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if out.returncode != 0:
        raise RuntimeError("gap 退出码 %d\nstdout: %s\nstderr: %s"
                           % (out.returncode, out.stdout[-500:], out.stderr[-500:]))
    return (out.stdout or "").strip().splitlines()[-1].strip() if out.stdout.strip() else ""


def main(argv):
    if len(argv) < 2:
        print("用法: test.py <conan 包根>", file=sys.stderr)
        return 2
    root = argv[1]
    gap_bin = os.path.join(root, "bin", "gap")
    # GAP 支持多 root，分号分隔：share/gap 是架构无关的主 root（lib/init.g、grp/、pkg/ 都在那），
    # lib/gap 放 sysinfo.gap 等架构相关件。只给一个会报 `cannot find 'lib/init.g'`。
    gap_root = "%s;%s" % (os.path.join(root, "share", "gap"), os.path.join(root, "lib", "gap"))
    if not os.path.isfile(gap_bin):
        print("[FAIL] 缺可执行文件: %s" % gap_bin)
        return 1
    checks = [
        ("Size(SymmetricGroup(5))", "120", "S5 的阶"),
        ("Size(SmallGroup(8,3))", "8", "SmallGroup(8,3) 的阶（需 smallgrp 包）"),
        ("NrPrimitiveGroups(8)", "7", "8 次本原群个数（需 primgrp 包）"),
    ]
    bad = 0
    for code, expect, desc in checks:
        try:
            got = run_gap(gap_bin, gap_root, code)
        except Exception as e:               # noqa: BLE001
            print("[FAIL] %s: %s" % (desc, e))
            bad += 1
            continue
        if got != expect:
            print("[FAIL] %s：期望 %s，实得 %r" % (desc, expect, got))
            bad += 1
        else:
            print("[PASS] %s = %s" % (desc, got))
    print("gap: %d 条断言，失败 %d 条" % (len(checks), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
