#!/usr/bin/env python3
"""上游功能测试用例生成器 — pari-nflistdata/20220729.

**用例集由被测目录枚举而来，不硬编码**（同族 pari-galpol/20180625 的
upstream-gp-sweep-generator.py 同法；gp 侧只做真实读取与比较）。

用法
    python3 upstream-gp-sweep-generator.py <datadir_root> [--family {qt,a5,all}]
                                                   [--out <file.gp>] [--print-cases]

  <datadir_root>  含 nflistdata/ 的目录，即 gp 的 `datadir`
                  （打包产物是 <pkg>/res/pari，上游解包树是 <work>）。

输出：一段 straight-line GP 脚本，第 1 行自带
    default(datadir,"<datadir_root>");
（历史踩坑：生成脚本若不写 datadir，gp 会用编译期内置路径，测的不是本包数据。）

用例族
  qt_<deg>_<idx>   nflist([deg,idx],'t) 读 nflistdata/<deg>/<idx>/QT，断言返回
                   t_POL、poldegree == deg、变量为 x（每个 QT 文件一条，共 650）。
  a5_*             A5(=5T4) 与 A5(6)(=[6,4]) 表的功能级断言（计数/边界/错误路径）。

GP 词法注意（实证于 pari/2.17.4.1 的 gp）
  * 该 gp **没有** `catch`/`file_exists`/`is_file`/`is_dir`/`wildcards`/`substr`
    等原语，故枚举与归因交给本 Python 侧，gp 只做读取与比较；
  * 注释里**禁止行尾反斜杠**：GP 词法按续行合并注释，会吃掉后面的函数定义，
    曾导致"整轮 0 用例却 rc=0"的静默空跑。
"""
import argparse
import os
import sys

A5_CASES = [
    # (用例名, GP 表达式, 期望判定用的 GP 布尔表达式)
    # 表内第二字段是 sqrt(|disc|)（实证：5/4/0/0 首行 1762 ↔ disc=1762^2 可被
    # nflist("A5",1762^2,0) 精确检索），故按 disc 查询用 B^2。
    ("a5_default_count",
     'nflist("A5")',
     '#A5D==10'),
    ("a5_r2_0_full_table",
     'nflist("A5", [1, 524286^2], 0)',
     '#A5F==15184'),
    ("a5_r2_2_full_table",
     'nflist("A5", [1, 10^8], 2)',
     '#A5T==2336'),
    ("a5_r2_0_subrange_monotone",
     'nflist("A5", [1, 10^8], 0)',
     '#A5S>0 && #A5S<#A5F'),
    ("a5_single_discriminant_roundtrip",
     'nflist("A5", 1762^2, 0)',
     '#A5P==1 && Str(A5P[1])=="x^5 - 11*x^3 - 5*x^2 + 18*x + 9"'),
    ("a5_6_regular_extension",
     'nflist([6,4], \'t)',
     'type(A64)=="t_POL" && poldegree(A64)==6'),
    ("a5_signature_r2_1_absent",
     'nflist("A5", [1, 10^8], 1)',
     '#A5U==0'),
    ("a5_out_of_range_domain_error",
     'nflist("A5", [1, 10^11], -1)',
     'type(A5X)=="t_POL" && Str(A5X)=="A5X"'),
]


def rel_datadir(root):
    """返回 (gp 的 datadir, 数据根 datadir/nflistdata 的绝对路径)。"""
    cand = os.path.join(root, "nflistdata")
    if os.path.isdir(cand):
        return root, cand
    if os.path.basename(os.path.normpath(root)) == "nflistdata":
        return os.path.dirname(os.path.normpath(root)), root
    sys.exit("错误：%s 下找不到 nflistdata/ 目录" % root)


def enum_qt(data_root):
    out = []
    for deg in os.listdir(data_root):
        p = os.path.join(data_root, deg)
        if not os.path.isdir(p) or not deg.isdigit():
            continue
        for idx in sorted(os.listdir(p), key=lambda s: (len(s), s)):
            q = os.path.join(p, idx, "QT")
            if os.path.isfile(q):
                out.append((int(deg), int(idx)))
    return sorted(out)


def parse_case_name(name):
    """qt_<deg>_<idx> -> (deg, idx)；a5_* -> 原样返回（语义用例走固定表）。"""
    if not name.startswith("qt_"):
        return None
    parts = name.split("_")
    if len(parts) != 3:
        return None
    try:
        return int(parts[1]), int(parts[2])
    except ValueError:
        return None


A5_VAR = {"a5_default_count": "A5D",
          "a5_r2_0_full_table": "A5F",
          "a5_r2_2_full_table": "A5T",
          "a5_r2_0_subrange_monotone": "A5S",
          "a5_single_discriminant_roundtrip": "A5P",
          "a5_6_regular_extension": "A64",
          "a5_signature_r2_1_absent": "A5U",
          "a5_out_of_range_domain_error": "A5X"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--family", choices=("qt", "a5", "all"), default="all")
    ap.add_argument("--out")
    ap.add_argument("--print-cases", action="store_true",
                    help="只打印期望用例名清单（驱动侧据此核对，防静默空跑）")
    ap.add_argument("--cases-from",
                    help="用例名清单文件（每行一个）。反向对照时复用**同一用例集**"
                         "但把 datadir 指向不含表的目录，用例集不随之缩减。")
    a = ap.parse_args()

    datadir, data_root = rel_datadir(a.root)
    if a.cases_from:
        with open(a.cases_from, encoding="utf-8") as fh:
            wanted = [ln.strip() for ln in fh
                      if ln.strip() and not ln.startswith("#")]
        qts = sorted({parse_case_name(c) for c in wanted
                      if parse_case_name(c)})
        a5s = [c for c in A5_CASES if c[0] in wanted]
    else:
        qts = enum_qt(data_root)
        a5s = list(A5_CASES)
    a5s = [(n, e, p) for (n, e, p) in a5s]

    cases = []
    if a.family in ("qt", "all"):
        cases += ["qt_%d_%d" % (d, i) for d, i in qts]
    if a.family in ("a5", "all"):
        cases += [c[0] for c in a5s]

    if a.print_cases:
        for c in cases:
            print(c)
        return 0

    lines = ['default(datadir,"%s");' % datadir.replace("\\", "\\\\")]
    if a.family in ("qt", "all"):
        for deg, idx in qts:
            v = "V%d_%d" % (deg, idx)
            lines.append("%s = nflist([%d,%d], 't);" % (v, deg, idx))
            lines.append(
                'print("qt_%d_%d ", if(type(%s)=="t_POL" && poldegree(%s)==%d '
                '&& variable(%s)==x, "PASS", "FAIL"));' % (deg, idx, v, v, deg, v))
    if a.family in ("a5", "all"):
        for name, expr, pred in a5s:
            var = A5_VAR[name]
            lines.append("%s = %s;" % (var, expr))
            lines.append('print("%s ", if(%s, "PASS", "FAIL"));' % (name, pred))

    body = "\n".join(lines) + "\n"
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(body)
        sys.stderr.write("wrote %s (%d cases)\n" % (a.out, len(cases)))
    else:
        sys.stdout.write(body)
    sys.stderr.write("expected cases: %d\n" % len(cases))
    return 0


if __name__ == "__main__":
    sys.exit(main())
