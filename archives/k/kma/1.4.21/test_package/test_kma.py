#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kma 1.4.21 消费者测试（Conan test_package / CI L1、R34 实质依赖）。

这个脚本**只做真实工作**：用打包进 bin/ 的 kma 可执行文件先建一个真实的
模板库（kma index），再用上游自带的 -mmap 非 SysV 路径做一次真实比对
（kma -i ... -t_db ... -mmap ...），最后逐字段核对输出数值与比对串。

为什么交付口径是 -mmap（不改上游一行代码）：
  本平台 seccomp-BPF 把 shmget/shmat/semget/msgget 等按 syscall 号击杀成
  SIGSYS(31)，而默认读库路径 hashMapKMA_load()（hashmapkma.c:275）在
  hashmapkma.c:319/349/385/416 无条件 ftok()+shmget() 探测，"探测失败就走
  普通文件读"的回退（hashmapkma.c:321-330）因此不可达。上游自己提供了
  -mmap（kma.c:144 帮助行，kma.c:525-527 置 shm|=32 并把 destroy 换成
  hashMapKMA_munmap；kmers.c:86-87 与 sparse.c:381-382 转向 kmmap.c:33 的
  hashMapKMAmmap，纯文件后端 mmap，本平台放行）。
  实测（本机、同一份库与输入）：不加 -mmap 的默认路径 rc=159（128+31=SIGSYS）
  且四个输出文件全 0 字节；加 -mmap rc=0 且结果与上游语义一致。
  证据文件路径见 notes.md 与 PR 正文。

断言清单（本文件里一共 12 条）：
  A1  kma -v 输出 KMA-1.4.21 且 rc=0
  A2  kma index rc=0
  A3  建库产物 testdb.comp.b 存在且 > 1 MiB（真实压缩库，非空壳）
  A4  建库产物 testdb.length.b 存在且非空
  A5  kma map -mmap rc=0
  A6  out_mmap.res 数据行恰好 1 行
  A7  Template == t1
  A8  Score == 300
  A9  Query_Identity == 100.00
  A10 Template_length == 600 且 Template_Coverage == 50.00（300/600bp）
  A11 Query_Coverage == 200.00（正负链各覆盖一次）
  A12 out_mmap.aln 头部为 "# t1"，含 5 段 60 连"|"的全匹配、5 段 60 连"_"的
      未覆盖段，且查询序列原文出现在文件里

用法：test_kma.py <kma 可执行文件绝对路径> <db.fa> <query.fa> <工作目录>
退出码：0 全部通过；1 任一断言失败；2 用法错误。
"""

import os
import subprocess
import sys

PIPE60 = "|" * 60
UNDER60 = "_" * 60
QUERY_FIRST_LINE = ("ctaaaccgtaggagtaaggcaaaacttgcggtaaaacttttatatgggttg"
                    "tcatacggg")

failures = []


def check(name, cond, detail=""):
    """记录并打印每一条断言的真实判决。"""
    if cond:
        print("[assert] PASS %s %s" % (name, detail))
    else:
        print("[assert] FAIL %s %s" % (name, detail))
        failures.append(name)
    return cond


def run(cmd, cwd):
    """执行真实命令，打印命令行与退出码（-mmap 因此出现在构建日志里）。"""
    print("[run] $ " + " ".join(cmd), flush=True)
    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True)
    lines = (p.stdout or "").splitlines()
    for ln in lines[-14:]:
        print("[run] | " + ln)
    print("[run] rc=%d (lines=%d)" % (p.returncode, len(lines)), flush=True)
    return p


def read_if_exists(path):
    if not os.path.isfile(path):
        return None
    with open(path, "r", errors="replace") as f:
        return f.read()


def main():
    if len(sys.argv) != 5:
        print("usage: test_kma.py <kma-bin> <db.fa> <query.fa> <workdir>",
              file=sys.stderr)
        return 2
    kma, db_fa, query_fa, ws = sys.argv[1:5]
    for path in (kma, db_fa, query_fa):
        if not os.path.isfile(path):
            print("[fatal] missing input: %s" % path, file=sys.stderr)
            return 1
    os.makedirs(ws, exist_ok=True)

    print("[info] kma binary : %s" % kma)
    print("[info] size       : %d bytes" % os.path.getsize(kma))
    print("[info] workdir    : %s" % ws)

    # ---- A1: 版本 ----------------------------------------------------------
    p = run([kma, "-v"], cwd=ws)
    check("A1 kma -v 报告 KMA-1.4.21 且 rc=0",
          p.returncode == 0 and "KMA-1.4.21" in (p.stdout or ""),
          "rc=%d out=%r" % (p.returncode, (p.stdout or "").strip()[:40]))

    # ---- A2..A4: 真建库 ----------------------------------------------------
    db = os.path.join(ws, "testdb")
    p = run([kma, "index", "-i", db_fa, "-o", db], cwd=ws)
    check("A2 kma index rc=0", p.returncode == 0, "rc=%d" % p.returncode)
    comp = db + ".comp.b"
    length = db + ".length.b"
    comp_size = os.path.getsize(comp) if os.path.isfile(comp) else -1
    check("A3 testdb.comp.b 存在且 > 1 MiB（真实压缩库）",
          comp_size > 1024 * 1024, "size=%d" % comp_size)
    len_size = os.path.getsize(length) if os.path.isfile(length) else -1
    check("A4 testdb.length.b 存在且非空", len_size > 0, "size=%d" % len_size)
    produced = sorted(f for f in os.listdir(ws) if f.startswith("testdb."))
    print("[info] index artifacts: %s" % produced)

    # ---- A5: 上游 -mmap 路径做真比对 --------------------------------------
    out = os.path.join(ws, "out_mmap")
    p = run([kma, "-i", query_fa, "-t_db", db, "-mmap", "-o", out], cwd=ws)
    check("A5 kma map -mmap rc=0", p.returncode == 0, "rc=%d" % p.returncode)

    # ---- A6..A11: .res 逐字段核数值 ---------------------------------------
    res = read_if_exists(out + ".res")
    rows = []
    if res:
        rows = [ln.split() for ln in res.splitlines()
                if ln.strip() and not ln.startswith("#")]
    header = []
    if res:
        for ln in res.splitlines():
            if ln.startswith("#"):
                header = ln.lstrip("#").split()
    print("[info] .res header: %s" % header)
    check("A6 .res 数据行恰好 1 行", len(rows) == 1, "rows=%d" % len(rows))
    col = {}
    if len(rows) == 1 and len(header) == len(rows[0]):
        col = dict(zip(header, rows[0]))
    print("[info] .res fields: %s" % col)
    check("A7 Template == t1", col.get("Template") == "t1",
          "got=%r" % col.get("Template"))
    check("A8 Score == 300", col.get("Score") == "300",
          "got=%r" % col.get("Score"))
    check("A9 Query_Identity == 100.00",
          col.get("Query_Identity") == "100.00",
          "got=%r" % col.get("Query_Identity"))
    check("A10 Template_length == 600 且 Template_Coverage == 50.00",
          col.get("Template_length") == "600"
          and col.get("Template_Coverage") == "50.00",
          "len=%r cov=%r" % (col.get("Template_length"),
                             col.get("Template_Coverage")))
    check("A11 Query_Coverage == 200.00",
          col.get("Query_Coverage") == "200.00",
          "got=%r" % col.get("Query_Coverage"))

    # ---- A12: .aln 内容 ----------------------------------------------------
    aln = read_if_exists(out + ".aln") or ""
    aln_lines = aln.splitlines()
    pipes = sum(1 for ln in aln_lines if PIPE60 in ln)
    unders = sum(1 for ln in aln_lines if UNDER60 in ln)
    check("A12 .aln 头部为 # t1、5 段全匹配、5 段未覆盖、含查询序列原文",
          bool(aln_lines) and aln_lines[0].strip() == "# t1"
          and pipes == 5 and unders == 5 and QUERY_FIRST_LINE in aln,
          "head=%r pipes=%d underscores=%d" %
          (aln_lines[0] if aln_lines else None, pipes, unders))

    for extra in (out + ".fsa", out + ".pair", out + ".summary"):
        if os.path.isfile(extra):
            print("[info] %s: %d bytes" % (os.path.basename(extra),
                                           os.path.getsize(extra)))

    if failures:
        print("[result] FAIL %d/%d assertions failed: %s"
              % (len(failures), 12, ", ".join(failures)))
        return 1
    print("[result] PASS 12/12 assertions (kma index + kma map -mmap)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
