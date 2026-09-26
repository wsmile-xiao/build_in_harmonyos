#!/usr/bin/env python3
"""test_package/test_trinculo.py — 消费已安装 trinculo 的真实功能断言。

用法: test_trinculo.py <binpath> <examples_dir> <work_dir>
全部走绝对路径（§一.14/止损先例 #5）；每条断言打印 `PASS - `/`FAIL - `，
conanfile 侧按行计数并以 FAIL 行判失败。
"""
import hashlib
import os
import subprocess
import sys

BIN = sys.argv[1]
EX = sys.argv[2]
WORK = sys.argv[3]

_passed = 0
_failed = 0


def check(name, cond, detail=""):
    global _passed, _failed
    if cond:
        _passed += 1
        print("PASS - " + name)
    else:
        _failed += 1
        print("FAIL - " + name + (" | " + detail if detail else ""))


def run_trinculo(args, out_prefix, timeout=120):
    """跑一次 trinculo，返回 (rc, stdout+stderr)。输出统一落 out_prefix.*。"""
    cmd = [BIN] + args + ["--out", out_prefix]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, "timeout after {}s".format(timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# ── 场景 1: --help 冒烟（rc=0 + Usage 横幅，inputparser.h:302 throw 1 → main 返 0）──
r = subprocess.run([BIN, "multinom", "--help"], capture_output=True, text=True, timeout=60)
check("--help rc==0", r.returncode == 0, "rc={}".format(r.returncode))
check("--help 输出含 Usage", "Usage:" in (r.stdout or ""), (r.stdout or "")[:80])

# ── 场景 2: 随包 dosage 样例真实跑（上游 test2 同参数）──
dose = os.path.join(EX, "genotypes.dose")
pheno = os.path.join(EX, "phenos.txt")
out2 = os.path.join(WORK, "tp2")
rc, log = run_trinculo(["multinom", "--dosage", dose, "--pheno", pheno,
                        "--phenoname", "Pheno", "--basepheno", "Control"], out2)
check("dosage 分析 rc==0", rc == 0, "rc={} log={}".format(rc, log[-200:]))
assoc2 = out2 + ".assoc.multinom"
check("dosage assoc 产物存在", os.path.isfile(assoc2), assoc2)
if os.path.isfile(assoc2):
    lines = open(assoc2).read().splitlines()
    check("dosage assoc 行数==6（header+5 SNP）", len(lines) == 6, "lines={}".format(len(lines)))
    check("dosage assoc 首行 RSID 表头", lines[0].startswith("RSID"), lines[0][:60])
    md5 = hashlib.md5(open(assoc2, "rb").read()).hexdigest()
    # 上游 bin/testing.py test2 golden（bytes 字面量解出的 hex，W0 实测
    # OHOS aarch64 clang15 产物与上游 2016 期望字节全等）
    check("dosage assoc golden MD5", md5 == "3d36d0b3d81553578ff98613999053ba", md5)
check("dosage log 含 Running trinculo v0.96",
      os.path.isfile(out2 + ".log") and "Running trinculo v0.96" in open(out2 + ".log").read())

# ── 场景 3: 随包 plink .bed 样例真实跑（上游 test1 同参数，读二进制 bed）──
bfile = os.path.join(EX, "genotypes")
out3 = os.path.join(WORK, "tp3")
rc, log = run_trinculo(["multinom", "--bfile", bfile, "--pheno", pheno,
                        "--phenoname", "Pheno", "--basepheno", "Control"], out3)
check("plink(bed) 分析 rc==0", rc == 0, "rc={} log={}".format(rc, log[-200:]))
assoc3 = out3 + ".assoc.multinom"
check("plink assoc 产物存在", os.path.isfile(assoc3), assoc3)
if os.path.isfile(assoc3):
    check("plink assoc 行数==6", len(open(assoc3).read().splitlines()) == 6)

# ── 场景 4: 确定性（同输入重跑字节全等）──
out4 = os.path.join(WORK, "tp4")
run_trinculo(["multinom", "--dosage", dose, "--pheno", pheno,
              "--phenoname", "Pheno", "--basepheno", "Control"], out4)
if os.path.isfile(assoc2) and os.path.isfile(out4 + ".assoc.multinom"):
    same = open(assoc2, "rb").read() == open(out4 + ".assoc.multinom", "rb").read()
    check("同输入两次输出字节全等", same)
else:
    check("同输入两次输出字节全等", False, "assoc missing")

# ── 场景 5: 错误路径非零退出（无 mode → rc=1，main() 分支）──
r = subprocess.run([BIN, "--nosuchmode"], capture_output=True, text=True, timeout=60)
check("未知 mode rc!=0", r.returncode != 0, "rc={}".format(r.returncode))

print("SUMMARY passed={} failed={}".format(_passed, _failed))
sys.exit(1 if _failed else 0)
