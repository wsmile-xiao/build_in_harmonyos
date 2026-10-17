#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_rs_consumer.py —— rs 的消费者视角功能测试（测试体系第 2 层，N_consumer=1 个程序）

以"装好之后要用 rs 的人"的身份，从安装包目录里取 bin/rs 真实执行并断言行为。
分工口径：与上游语料**逐字节**对齐的部分由第 1 层 check_t_runner.py 负责（13 条
用例已在 conan create 日志里逐条打出），本文件做的是**结构与语义**断言，重点
覆盖两处本包特有的兼容链路：

  C1 列重排：``rs 3 3`` 把 9 个字段排成 3×3，行/列内容与行数正确
  C2 空字段：``rs -c 0 2`` 空字段仍占位、各行等宽（rs 的核心行为）
  C3 转置 + 宽列：``rs -e 0 5`` 每行一个条目、列序正确、两行等宽
  C4 strtonum 兼容链路语义：非数字参数 → 上游 .linked/strtonum.c 的 "invalid"
     + 非 0 退出码（证明补进来的实现真在链路上，而不是"能链接"就算过）
  C5 同上越界分支 → "too large"
  C6 reallocarray 扩容路径：5000 行 × 6 字段 → 退出码 0 且字段多重集合守恒
     （混链静态 libc 时这里必 SIGSEGV，故本条同时是那件事的回归哨兵）
  C7 UTF-8 显示宽度：LC_ALL=C.UTF-8 下多字节/宽字符参与列宽计算

断言失败即非 0 退出。测试按传入路径调用被测二进制，不做"文件存在就算过"的
假断言 ⇒ 把包目录改名后 conan test 必然失败（L1e 破坏性反向验证成立）。
"""
import collections
import os
import subprocess
import sys

FAILURES = []


def run(exe, args, stdin=b"", env=None):
    child_env = dict(os.environ)
    if env:
        child_env.update(env)
    return subprocess.run([exe] + args, input=stdin, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, env=child_env, timeout=120)


def check(label, condition, detail=""):
    print("%s    %-28s %s" % ("PASS" if condition else "FAIL", label, detail))
    if not condition:
        FAILURES.append(label)


def rows_of(stdout_bytes):
    """stdout → 去掉尾部空行后的行列表（rs 每行都以 \\n 结尾）。"""
    lines = stdout_bytes.split(b"\n")
    while lines and lines[-1] == b"":
        lines.pop()
    return lines


def display_width(text):
    """按 wcwidth 口径算显示宽度：东亚宽/全角字符占 2 列，其余占 1 列。

    用它（而不是字节长度）来断言 rs 的列对齐，才能真正检验"UTF-8 宽度"这条
    链路：rs 的 utf8.c 走 mbsavis()/wcwidth()，若宽度算错，三行的显示宽度就
    不会相等。
    """
    import unicodedata

    total = 0
    for char in text:
        if unicodedata.combining(char):
            continue
        total += 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
    return total


def main(argv):
    if len(argv) < 2:
        sys.stderr.write("usage: %s <path-to-rs>\n" % os.path.basename(argv[0]))
        return 2
    exe = argv[1]
    if not os.path.isfile(exe):
        print("FAIL    binary-under-test-missing     %s" % exe)
        return 1

    # C1 ── 9 个字段排成 3×3
    proc = run(exe, ["3", "3"], b"1\n2\n3\n4\n5\n6\n7\n8\n9\n")
    rows = rows_of(proc.stdout)
    got = [line.split() for line in rows]
    check("C1_reshape_3x3",
          proc.returncode == 0 and got == [[b"1", b"2", b"3"], [b"4", b"5", b"6"],
                                           [b"7", b"8", b"9"]],
          "rc=%d rows=%s" % (proc.returncode, got))

    # C2 ── 空字段占位 + 各行等宽（上游语料 debian-706717-r1.10 的同一输入）
    proc = run(exe, ["-c", "0", "2"], b"0\t0\n\t0\n")
    rows = rows_of(proc.stdout)
    check("C2_empty_field",
          proc.returncode == 0 and len(rows) == 2 and len(set(map(len, rows))) == 1
          and rows[0].split() == [b"0", b"0"] and rows[1].split() == [b"0"],
          "rc=%d rows=%r" % (proc.returncode, rows))

    # C3 ── 每行一个条目（含空格的整体）+ 等宽（上游语料 debian-650029-e 同输入）
    wide_in = b"1\na wide column\n2\n3\n4\na\nanother wide column\nb\nc\nd\n"
    proc = run(exe, ["-e", "0", "5"], wide_in)
    rows = rows_of(proc.stdout)
    check("C3_transpose_wide",
          proc.returncode == 0 and len(rows) == 2 and len(set(map(len, rows))) == 1
          and rows[0].count(b"a wide column") == 1
          and rows[1].count(b"another wide column") == 1,
          "rc=%d rows=%d widths=%s" % (proc.returncode, len(rows), list(map(len, rows))))

    # C4 ── strtonum：非数字 → 上游兼容实现给出的 "invalid"
    proc = run(exe, ["abc", "2"], b"a b\n")
    check("C4_strtonum_invalid",
          proc.returncode != 0 and b"invalid" in proc.stderr,
          "rc=%d stderr=%r" % (proc.returncode, proc.stderr.strip()[:64]))

    # C5 ── strtonum：越界 → "too large"（ERANGE 分支）
    proc = run(exe, ["0", "99999999999999999999"], b"a b\n")
    check("C5_strtonum_too_large",
          proc.returncode != 0 and b"too large" in proc.stderr,
          "rc=%d stderr=%r" % (proc.returncode, proc.stderr.strip()[:64]))

    # C6 ── reallocarray 扩容：字段多重集合守恒（不丢、不重、不截断）
    stdin = b"".join(b"a b c d e f\n" for _ in range(5000))
    proc = run(exe, ["-e", "0", "7"], stdin)
    src = collections.Counter(stdin.split())
    got = collections.Counter(proc.stdout.split())
    check("C6_reallocarray_growth",
          proc.returncode == 0 and got == src and sum(src.values()) == 30000,
          "rc=%d out_lines=%d fields=%d/%d"
          % (proc.returncode, len(rows_of(proc.stdout)), sum(got.values()), sum(src.values())))

    # C7 ── UTF-8 显示宽度：列对齐按"显示宽度"而非字节数（上游语料 unicode-1 同输入）
    uni_in = "mäh miau a Kuh 猫 b ❣❧ マヌル c\n".encode("utf-8")
    proc = run(exe, ["0", "3"], uni_in, env={"LC_ALL": "C.UTF-8"})
    rows = rows_of(proc.stdout)
    cells = [row.decode("utf-8").split() for row in rows]
    widths = {display_width(row.decode("utf-8")) for row in rows}
    check("C7_utf8_width",
          proc.returncode == 0 and len(rows) == 3 and len(widths) == 1
          and cells == [["mäh", "miau", "a"], ["Kuh", "猫", "b"], ["❣❧", "マヌル", "c"]],
          "rc=%d rows=%d display_widths=%s cells=%s"
          % (proc.returncode, len(rows), sorted(widths), cells))

    print("CONSUMER_SUMMARY cases=7 pass=%d fail=%d" % (7 - len(FAILURES), len(FAILURES)))
    print("CONSUMER_VERDICT %s" % ("PASS" if not FAILURES else "FAIL"))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
