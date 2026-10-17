#!/usr/bin/env python3
"""palp 真实计算断言（独立可跑：`python3 test.py <bin目录>`）。

期望值不是编的：`tests/2.1-polytope-input.sh` 里写死
    COMMAND="./poly-${DIM}d.x tests/input/2.1-polytope-input.txt"
    EXPECTED="M:6 3 F:3"
输入文件内容也逐字来自 `tests/input/2.1-polytope-input.txt`。

手算可验：二维三角形 (0,0)(2,0)(0,2) 有 6 个格点、3 个顶点、3 条边 → M:6 3 F:3。

跑两个二进制而不是一个：`poly.x`（Global.h 默认 POLY_Dmax=6）与 `poly-11d.x`
必须给出**同样**的结论 —— 这一条专防「按维度分别编译」那套矩阵编歪了
（复用了错误维度的 .o，结果会不一致）。
"""
import os
import subprocess
import sys
import tempfile

EXPECTED = "M:6 3 F:3"
POLYTOPE = "3 2 This text is ignored by PALP\n2 0\n0 2\n0 0\n"


def main(argv):
    if len(argv) < 2:
        print("用法: test.py <bin目录>", file=sys.stderr)
        return 2
    bindir = argv[1]
    tmpdir = tempfile.mkdtemp()
    infile = os.path.join(tmpdir, "polytope.txt")
    with open(infile, "w", encoding="utf-8") as f:
        f.write(POLYTOPE)

    failed = 0
    for prog in ("poly.x", "poly-11d.x"):
        exe = os.path.join(bindir, prog)
        if not os.path.isfile(exe):
            print("[FAIL] 缺可执行文件: %s" % exe)
            failed += 1
            continue
        # 绝对路径调用：这份 musl 上的 exec 不做 PATH 查找，裸名会 ENOENT
        out = subprocess.run([exe, infile], capture_output=True, text=True, timeout=300)
        actual = (out.stdout or "").strip()
        if out.returncode != 0:
            print("[FAIL] %s 退出码 %d: %s" % (prog, out.returncode, out.stderr[-300:]))
            failed += 1
        elif actual != EXPECTED:
            print("[FAIL] %s 输出不符\n  期望: %s\n  实得: %s" % (prog, EXPECTED, actual))
            failed += 1
        else:
            print("[PASS] %s: %s" % (prog, actual))

    print("palp: %d 条断言，失败 %d 条" % (2, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
