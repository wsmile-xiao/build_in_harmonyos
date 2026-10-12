#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""boot 1.3-32 R-free 包树校验器（实质测试，R34；仅用 Python 标准库）。

用法::

    python3 validate_boot.py <dir>

``<dir>`` 既可以是**安装后的包树根**，也可以是**上游源码树根**：

1. 若 ``<dir>/lib/R/library/boot`` 存在 → 校验该 R 库树（安装后形态，
   test_package 使用）；
2. 否则 → 直接把 ``<dir>`` 当作 R 包树根校验（源码树形态，build() 阶段使用）。

校验项（全部计数，最终打印 ``assertions=<N> failures=<N>`` 与
``BOOT_VALIDATE_PASS``；任何失败打印明细并非零退出）：

A. DESCRIPTION 逐字段：Package/Version/NeedsCompilation/License/Depends/
   LazyData/ByteCompile；
B. NAMESPACE 导出名集合 **完全等于** 脚本内嵌的期望集合（36 个，写死）+
   import(stats) + importFrom(graphics, ...) 8 项 + 7 条 S3method；
C. 每个导出名都能在 R/bootfuns.q 或 R/bootpracs.q 中找到
   ``^\\s*<name>\\s*<-\\s*function`` 定义；
D. data/ 下 .rda == 50 个，每个 gzip 魔数 1f 8b + 可解压 + 解压后前 5 字节属
   {RDX2\\n, RDX3\\n, RDA2\\n, RDA3\\n}；另抽查 12 个数据集的列名
   （CHARSXP 序列化字节）；
E. man/ 下 .Rd == 88 个，含 examples 的 == 25 个；
F. tests/parallel-censboot.R 含 censboot + parallel="multicore"；
   tests/Examples/boot-Ex.Rout.save 存在且含 915 条 "^> " 输入行；
G. 负向自检：不存在路径 / 复制树后删掉 NAMESPACE / 复制树后删掉 data/ 必须失败。

注意：``<dir>`` 传入安装后的包目录而 ``lib/`` 被移走时，本脚本回退到以 ``<dir>``
为 R 包树根，此时 DESCRIPTION 等核心文件不存在 → 必然失败（CI L1e 破坏性反向
验证依赖这一性质）。
"""
import gzip
import os
import re
import shutil
import struct
import sys
import tempfile

# ── 期望值（全部来自 boot_1.3-32.tar.gz 本地实测，写死以便回归） ──────────────

# NAMESPACE 中 export(...) 名单（36 个）
EXPECTED_EXPORTS = frozenset([
    "abc.ci", "boot", "boot.array", "boot.ci", "censboot", "control", "corr",
    "cum3", "cv.glm", "EEF.profile", "EL.profile", "empinf", "envelope",
    "exp.tilt", "freq.array", "glm.diag", "glm.diag.plots", "imp.moments",
    "imp.prob", "imp.quantile", "imp.weights", "inv.logit", "jack.after.boot",
    "k3.linear", "lik.CI", "linear.approx", "logit", "nested.corr", "norm.ci",
    "saddle", "saddle.distn", "simplex", "smooth.f", "tilt.boot", "tsboot",
    "var.linear",
])
N_EXPORTS = 36

# importFrom(graphics, ...) 的 8 个符号
EXPECTED_GRAPHICS = frozenset([
    "abline", "hist", "identify", "layout", "lines", "par", "plot", "text",
])

# 7 条 S3method（注册但不在 export 名单中）
EXPECTED_S3METHODS = frozenset([
    "c.boot", "lines.saddle.distn", "plot.boot", "print.boot", "print.bootci",
    "print.saddle.distn", "print.simplex",
])

# DESCRIPTION 期望字段（逐字段精确比对）
DCF_EXPECTED = (
    ("Package", "boot"),
    ("Version", "1.3-32"),
    ("NeedsCompilation", "no"),
    ("License", "Unlimited"),
    ("LazyData", "yes"),
    ("ByteCompile", "yes"),
)
DCF_DEPENDS_MUST_CONTAIN = ("R (>= 3.0.0)", "graphics", "stats")

# data/ 下的数据集数量与 .rda 序列化魔数
N_RDA = 50
RDATA_MAGICS = (b"RDX2\n", b"RDX3\n", b"RDA2\n", b"RDA3\n")

# man/ 页数量与其中含 examples 的数量
N_MAN = 88
N_MAN_EXAMPLES = 25

# 上游示例输出文件的行数（"^> " 输入表达式）
N_EXAMPLE_LINES = 915

# 抽查数据集 → 期望列名（本机解压 .rda 后用 CHARSXP 序列化确认）
EXPECTED_COLUMNS = {
    "aml": ("time", "cens", "group"),
    "aids": ("year", "quarter", "delay", "dud"),
    "nuclear": ("cost", "date", "t1", "t2", "cap", "pr", "ne", "ct", "bw",
                "cum.n", "pt"),
    "melanoma": ("time", "status", "sex", "age", "year", "thickness", "ulcer"),
    "poisons": ("time", "poison", "treat"),
    "catsM": ("Sex", "Bwt", "Hwt"),
    "channing": ("sex", "entry", "exit", "time", "cens"),
    "nitrofen": ("conc", "brood1", "brood2", "brood3", "total"),
    "nodal": ("aged", "stage", "grade", "xray", "acid"),
    "survival": ("dose", "surv"),
    "salinity": ("sal", "lag", "trend", "dis"),
    "hirose": ("volt", "time", "cens"),
}


class Checker(object):
    """极简断言累加器：记录断言总数与失败数。"""

    def __init__(self):
        self.assertions = 0
        self.failures = 0
        self.messages = []

    def check(self, cond, msg):
        self.assertions += 1
        if not cond:
            self.failures += 1
            self.messages.append("FAIL: " + msg)
        return bool(cond)

    def eq(self, actual, expected, msg):
        return self.check(
            actual == expected,
            "%s (expected %r, got %r)" % (msg, expected, actual))


def _read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def parse_dcf(text):
    """解析 R DESCRIPTION（DCF）为 {字段: 值}，续行按空格拼接。"""
    fields = {}
    current = None
    for line in text.splitlines():
        if not line.strip():
            continue
        if line[0] not in (" ", "\t") and ":" in line:
            key, value = line.split(":", 1)
            current = key.strip()
            fields[current] = value.strip()
        elif current is not None:
            fields[current] = (fields[current] + " " + line.strip()).strip()
    return fields


def _charsxp(name):
    """R 序列化中一个 CHARSXP 字符串的前缀字节（长度前缀 + 内容）。"""
    raw = name.encode("utf-8")
    return b"\x00\x00\x04\t" + struct.pack(">i", len(raw)) + raw


def resolve_tree(root):
    """安装后形态优先；否则把 root 自身当 R 包树根。"""
    installed = os.path.join(root, "lib", "R", "library", "boot")
    if os.path.isdir(installed):
        return installed
    return root


def validate_tree(tree, ck):
    """对 R 包树 tree 执行全部正向校验，结果累计进 ck。"""

    # ── A. DESCRIPTION ───────────────────────────────────────────────
    desc_path = os.path.join(tree, "DESCRIPTION")
    ck.check(os.path.isfile(desc_path), "DESCRIPTION exists at %s" % desc_path)
    fields = {}
    if os.path.isfile(desc_path):
        fields = parse_dcf(_read_text(desc_path))
    for key, expected in DCF_EXPECTED:
        ck.eq(fields.get(key), expected, "DESCRIPTION %s" % key)
    depends = fields.get("Depends", "")
    for token in DCF_DEPENDS_MUST_CONTAIN:
        ck.check(token in depends,
                 "DESCRIPTION Depends contains %r (got %r)" % (token, depends))

    # ── B. NAMESPACE ─────────────────────────────────────────────────
    ns_path = os.path.join(tree, "NAMESPACE")
    ck.check(os.path.isfile(ns_path), "NAMESPACE exists at %s" % ns_path)
    ns_text = _read_text(ns_path) if os.path.isfile(ns_path) else ""

    export_match = re.search(r"export\((.*?)\)", ns_text, re.S)
    exports = set()
    if export_match:
        block = export_match.group(1).replace("\n", " ")
        exports = set(part.strip() for part in block.split(",") if part.strip())
    ck.eq(len(exports), N_EXPORTS, "NAMESPACE export count")
    ck.check(exports == set(EXPECTED_EXPORTS),
             "NAMESPACE export set == expected 36 names "
             "(missing=%s extra=%s)"
             % (sorted(EXPECTED_EXPORTS - exports), sorted(exports - EXPECTED_EXPORTS)))

    ck.check(re.search(r"^\s*import\(stats\)", ns_text, re.M) is not None,
             "NAMESPACE has import(stats)")
    gfx_match = re.search(r"importFrom\(\s*graphics\s*,(.*?)\)", ns_text, re.S)
    graphics = set()
    if gfx_match:
        graphics = set(p.strip() for p in gfx_match.group(1).split(",") if p.strip())
    ck.check(graphics == set(EXPECTED_GRAPHICS),
             "NAMESPACE importFrom(graphics, ...) == 8 expected symbols "
             "(missing=%s extra=%s)"
             % (sorted(EXPECTED_GRAPHICS - graphics), sorted(graphics - EXPECTED_GRAPHICS)))
    # S3method(generic, class) 注册的方法全名为 generic.class
    s3methods = set(
        "%s.%s" % (generic, klass)
        for generic, klass in re.findall(
            r"^\s*S3method\(\s*([A-Za-z0-9._]+)\s*,\s*([A-Za-z0-9._]+)\s*\)",
            ns_text, re.M)
    )
    ck.check(s3methods == set(EXPECTED_S3METHODS),
             "NAMESPACE has exactly the 7 expected S3method entries "
             "(got=%s)" % sorted(s3methods))

    # ── C. 导出名均在 R/*.q 中有函数定义 ─────────────────────────────
    r_dir = os.path.join(tree, "R")
    q_files = ("bootfuns.q", "bootpracs.q")
    q_text = ""
    for qf in q_files:
        q_path = os.path.join(r_dir, qf)
        ck.check(os.path.isfile(q_path), "R/%s exists" % qf)
        if os.path.isfile(q_path):
            q_text += _read_text(q_path) + "\n"
    for name in sorted(EXPECTED_EXPORTS):
        defined = re.search(r"^\s*" + re.escape(name) + r"\s*<-\s*function", q_text, re.M)
        ck.check(defined is not None,
                 "export %r defined as `<name> <- function` in R/*.q" % name)

    # ── D. data/ .rda 序列化与列名 ───────────────────────────────────
    data_dir = os.path.join(tree, "data")
    ck.check(os.path.isdir(data_dir), "data/ exists at %s" % data_dir)
    rda_files = []
    if os.path.isdir(data_dir):
        rda_files = sorted(f for f in os.listdir(data_dir) if f.endswith(".rda"))
    ck.eq(len(rda_files), N_RDA, "data/ .rda file count")

    for fname in rda_files:
        fpath = os.path.join(data_dir, fname)
        with open(fpath, "rb") as fh:
            magic = fh.read(2)
        ck.check(magic == b"\x1f\x8b", "%s gzip magic 1f 8b" % fname)
        blob = b""
        ok = False
        try:
            with gzip.open(fpath, "rb") as gz:
                blob = gz.read()
            ok = True
        except Exception as exc:  # 报告到底层错误即算失败
            ck.check(False, "%s decompressible (%s)" % (fname, exc))
        if ok:
            ck.check(True, "%s decompressible" % fname)
        ck.check(blob[:5] in RDATA_MAGICS,
                 "%s serialization header in %s (got %r)"
                 % (fname, sorted(m.decode().strip() for m in RDATA_MAGICS), blob[:5]))

    for dataset in sorted(EXPECTED_COLUMNS):
        fpath = os.path.join(data_dir, dataset + ".rda")
        if not os.path.isfile(fpath):
            ck.check(False, "dataset %s present" % dataset)
            continue
        with gzip.open(fpath, "rb") as gz:
            blob = gz.read()
        missing = [col for col in EXPECTED_COLUMNS[dataset]
                   if _charsxp(col) not in blob]
        ck.check(not missing,
                 "dataset %s exposes expected column names %s (missing=%s)"
                 % (dataset, list(EXPECTED_COLUMNS[dataset]), missing))

    # ── E. man/ 页数与 examples ──────────────────────────────────────
    man_dir = os.path.join(tree, "man")
    ck.check(os.path.isdir(man_dir), "man/ exists at %s" % man_dir)
    rd_files = []
    examples_with_examples = []
    if os.path.isdir(man_dir):
        rd_files = sorted(f for f in os.listdir(man_dir) if f.endswith(".Rd"))
        for fname in rd_files:
            if re.search(r"^\\examples", _read_text(os.path.join(man_dir, fname)), re.M):
                examples_with_examples.append(fname)
    ck.eq(len(rd_files), N_MAN, "man/ .Rd file count")
    ck.eq(len(examples_with_examples), N_MAN_EXAMPLES,
          "man/ .Rd with examples count")

    # ── F. 上游测试资产 ─────────────────────────────────────────────
    tests_dir = os.path.join(tree, "tests")
    parallel = os.path.join(tests_dir, "parallel-censboot.R")
    ck.check(os.path.isfile(parallel), "tests/parallel-censboot.R exists")
    parallel_text = _read_text(parallel) if os.path.isfile(parallel) else ""
    ck.check("censboot" in parallel_text,
             "tests/parallel-censboot.R calls censboot")
    ck.check(re.search(r'parallel\s*=\s*"multicore"', parallel_text) is not None,
             'tests/parallel-censboot.R uses parallel="multicore"')

    rout_save = os.path.join(tests_dir, "Examples", "boot-Ex.Rout.save")
    ck.check(os.path.isfile(rout_save), "tests/Examples/boot-Ex.Rout.save exists")
    if os.path.isfile(rout_save):
        n_lines = sum(1 for line in _read_text(rout_save).splitlines()
                      if line.startswith("> "))
        ck.eq(n_lines, N_EXAMPLE_LINES,
              "tests/Examples/boot-Ex.Rout.save example input lines")


def _remove_if_exists(path):
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path, ignore_errors=True)
    elif os.path.exists(path):
        os.remove(path)


def _run_quiet(tree):
    """对给定树跑一次校验，返回 Checker（用于负向自检）。"""
    ck = Checker()
    validate_tree(tree, ck)
    return ck


def _run_negatives(tree, ck):
    """负向自检：必须失败的场景必须真的失败。"""
    # 1) 不存在的路径
    bogus = os.path.join(tempfile.gettempdir(), "boot_validate_missing_tree")
    ck.check(_run_quiet(resolve_tree(bogus)).failures > 0,
             "negative: nonexistent path must fail validation")

    tmp_root = tempfile.mkdtemp(prefix="boot_validate_neg_")
    scenarios = (
        ("no_namespace", "tree without NAMESPACE",
         lambda d: _remove_if_exists(os.path.join(d, "NAMESPACE"))),
        ("no_data", "tree without data/",
         lambda d: _remove_if_exists(os.path.join(d, "data"))),
    )
    try:
        for slug, label, mutate in scenarios:
            dst = os.path.join(tmp_root, slug)
            if os.path.isdir(tree):
                shutil.copytree(tree, dst)
            else:
                os.makedirs(dst, exist_ok=True)
            mutate(dst)
            ck.check(_run_quiet(dst).failures > 0,
                     "negative: %s must fail validation" % label)
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: validate_boot.py <dir>\n")
        return 2
    root = argv[1]
    ck = Checker()

    print("[validate_boot] root=%s" % root)
    tree = resolve_tree(root)
    print("[validate_boot] R package tree=%s" % tree)
    validate_tree(tree, ck)
    print("[validate_boot] positive checks: assertions=%d failures=%d"
          % (ck.assertions, ck.failures))

    before = ck.assertions, ck.failures
    _run_negatives(tree, ck)
    print("[validate_boot] negative checks: assertions=%d failures=%d"
          % (ck.assertions - before[0], ck.failures - before[1]))

    for message in ck.messages:
        print(message)
    print("assertions=%d failures=%d" % (ck.assertions, ck.failures))
    if ck.failures:
        print("BOOT_VALIDATE_FAIL")
        return 1
    print("BOOT_VALIDATE_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
