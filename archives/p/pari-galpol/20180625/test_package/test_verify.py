#!/usr/bin/env python3
"""test_package 内容级校验 — pari-galpol/20180625（R34：实质依赖被测包）.

用法: python3 test_verify.py <packaged_galpol_dir>

被测对象是 pari-galpol 包 **真实打包出来的字节**（<pkg>/res/pari/galpol），
不是本脚本里的常量表：任何文件丢失、截断、错位、被压缩替换都会红。

基线指纹来自官方源 galpol.tgz（sha256 562af283…16bb01b）解包后按**相对路径排序**
逐类/整体拼接计算，见 notes.md「基线指纹」小节。

统计口径说明：本文件是**打包校验**，不是上游测试统计。上游没有自动化测试
（包内 0 个 Makefile/configure/test 文件，Debian rules 无 check 目标，无
debian/tests/）；真实功能入口是消费方 gp 的 `galoisgetpol`，已用已发布的
pari/2.17.4 二进制对全部条目实跑 7337 项断言（7337 PASS / 0 FAIL），命令与统计见
test_package/MANIFEST.yml 与 notes.md；原始逐用例日志已入仓（upstream-test-cases.txt）；其余运行日志在本地 reports/
（仓库 .gitignore 的 `reports/` 条目使其不入 PR，可按 MANIFEST.yml 的命令复现）。
"""
import hashlib
import os
import re
import sys

# ── 上游基线（源 tarball 实测，非人为设定）────────────────────────────────
TOTAL_ENTRIES = 14681           # 含 README
COUNTS = {"real": 3657, "complex": 3537, "group": 3657,
          "name": 3657, "nb": 143, "non-wss": 29}
DATA_BYTES = 28536355           # 不含 README 的数据字节总数
ALL_DATA_SHA = "08b4b31de8b040afe347f4af544d54216687ad4319140aabe7ed7aa2dbc8e52c"
CLASS_SHA = {
    "complex": "b6c9b12c7ce9692bb8050dc726d85524273cc666681844fe97390ace25afef0e",
    "group":   "dc6cc331cae663b5a6f1e58c300b8e67b13151ea78169170daf08f988d3a0850",
    "name":    "6887e2164c481eb7a7cb472da9a75351da87db24985ec54a86ac2fb26668b6fb",
    "nb":      "b819e599380fadd909ea6185ab4803a3de54282fe7cf6e1a6edfaa25dbb7b63e",
    "non-wss": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "real":    "f413d1858ade9238cafab8e7f9b766eda76560a312dfd42904ab16da2f15129d",
}
README_SHA = "bd749aadab9df5610db75ed0ad175a2feb8c9f0e933d91330e8f7449e2ac8e1a"
SPOT_SHA = {
    "8/nb":         "f0b5c2c2211c8d67ed15e75e656c7862d086e9245420892a7de62cd9ec582a06",
    "8/1/real":     "3e33b762d2326402fb9230f18461cbed8f08940ab15a5d9f46f103f11572e047",
    "8/1/complex":  "e87c3f20aa14a7e02948d01d815fc5884e1b3ea39f28cb6257ed582228e9088a",
    "8/1/group":    "145f8e538bd59f9bdddc307fe402c611a7e3f5c9c8ace07a8836898d479dba20",
    "8/1/name":     "c9ebd402ed1b1eb1368baa2fad44fdd30720e4e1de14883011a4ec3b95890982",
    "1/1/real":     "e897c8a0c0073e5b6d52677d328fed9db3da10da4f2aa95d7cd83e6ab1629acf",
    "60/1/complex": "0c130bb4321470c3b3d4b43150d85f2e550521ea5ba31df448a1d8ff42c38abf",
    "143/nb":       "4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865",
}
# GP 文本语法：数据文件形如 [Pol([c0,…,cn]),den]
RE_POL = re.compile(rb"^\[Pol\(\[[0-9,\-]+\]\),[0-9]+\]$")
RE_NAME = re.compile(rb'^".*"$', re.S)
RE_NB = re.compile(rb"^[0-9]+$")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h


results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print("%-46s %s%s" % (name, "PASS" if ok else "FAIL",
                          ("  # " + detail) if detail else ""))
    return ok


def main(root):
    if not os.path.isdir(root):
        print("FAIL: 打包数据目录不存在: %s" % root)
        return 1

    entries = []
    for dp, _dn, fn in os.walk(root):
        for f in fn:
            rel = os.path.relpath(os.path.join(dp, f), root).replace(os.sep, "/")
            entries.append(rel)
    entries.sort()

    check("C01_packaged_dir_readable", len(entries) > 0, "%d files" % len(entries))
    check("C02_README_sha256",
          os.path.isfile(os.path.join(root, "README"))
          and sha256_file(os.path.join(root, "README")).hexdigest() == README_SHA)

    # 阶目录集合必须正好是 1..143
    orders = sorted(int(d) for d in os.listdir(root) if d.isdigit())
    check("C03_order_dirs_are_1_to_143",
          orders == list(range(1, 144)), "%d dirs" % len(orders))

    # 每个阶目录都要有 nb，且 nb 的值 == 该阶下组子目录个数（索引自洽）
    bad_nb = []
    for n in orders:
        nbp = os.path.join(root, str(n), "nb")
        if not os.path.isfile(nbp):
            bad_nb.append("%s:missing-nb" % n)
            continue
        val = open(nbp, "rb").read().strip()
        if not RE_NB.match(val):
            bad_nb.append("%s:not-integer" % n)
            continue
        got = len([d for d in os.listdir(os.path.join(root, str(n))) if d.isdigit()])
        if int(val) != got:
            bad_nb.append("%s:nb=%s dirs=%d" % (n, val.decode(), got))
    check("C04_nb_matches_group_dirs_143of143", not bad_nb, ";".join(bad_nb[:5]))

    # 分类计数
    from collections import Counter
    bases = Counter(e.rsplit("/", 1)[-1] for e in entries)
    for kind, exp in sorted(COUNTS.items()):
        check("C05_count_%s" % kind.replace("-", "_"), bases.get(kind, 0) == exp,
              "%d/%d" % (bases.get(kind, 0), exp))
    check("C06_total_entries_incl_README", len(entries) == TOTAL_ENTRIES,
          "%d/%d" % (len(entries), TOTAL_ENTRIES))

    # 未知文件（含 gzip 混入 / 扩展名）必须为 0
    unknown = sorted({e.rsplit("/", 1)[-1] for e in entries
                      if e.rsplit("/", 1)[-1] not in set(COUNTS) | {"README"}})
    check("C07_no_unexpected_or_compressed_files", not unknown, ";".join(unknown[:5]))

    # 字节级：总字节 + 整体拼接哈希 + 分类拼接哈希
    h_all = hashlib.sha256()
    h_cls = {k: hashlib.sha256() for k in COUNTS}
    total = 0
    for rel in entries:
        if rel == "README":
            continue
        with open(os.path.join(root, rel), "rb") as fh:
            b = fh.read()
        total += len(b)
        h_all.update(b)
        h_cls[rel.rsplit("/", 1)[-1]].update(b)
    check("C08_data_bytes_total", total == DATA_BYTES, "%d/%d" % (total, DATA_BYTES))
    got = h_all.hexdigest()
    check("C09_concat_sha256_all_data", got == ALL_DATA_SHA, got[:16] + "…")
    for kind in sorted(CLASS_SHA):
        g = h_cls[kind].hexdigest()
        check("C10_concat_sha256_class_%s" % kind.replace("-", "_"),
              g == CLASS_SHA[kind], g[:16] + "…")

    # 单文件抽查
    for rel in sorted(SPOT_SHA):
        p = os.path.join(root, rel)
        g = sha256_file(p).hexdigest() if os.path.isfile(p) else "MISSING"
        check("C11_spot_%s" % rel.replace("/", "_"), g == SPOT_SHA[rel], g[:16] + "…")

    # GP 语法（全量，非抽样）
    bad_pol = bad_name = bad_nbfmt = 0
    for rel in entries:
        base = rel.rsplit("/", 1)[-1]
        if base in ("real", "complex", "group"):
            with open(os.path.join(root, rel), "rb") as fh:
                data = fh.read().strip()
            if not data:
                bad_pol += 1
            elif base != "group" and not RE_POL.match(data):
                bad_pol += 1
        elif base == "name":
            with open(os.path.join(root, rel), "rb") as fh:
                data = fh.read().strip()
            if not RE_NAME.match(data):
                bad_name += 1
        elif base == "nb":
            with open(os.path.join(root, rel), "rb") as fh:
                data = fh.read().strip()
            if not RE_NB.match(data):
                bad_nbfmt += 1
    check("C12_gp_syntax_real_complex_group_nonempty",
          bad_pol == 0, "bad=%d" % bad_pol)
    check("C13_gp_syntax_name_quoted", bad_name == 0, "bad=%d" % bad_name)
    check("C14_gp_syntax_nb_integer", bad_nbfmt == 0, "bad=%d" % bad_nbfmt)

    # non-wss 标记必须是 0 字节占位（语义标记，不携带数据）
    nz = [e for e in entries if e.rsplit("/", 1)[-1] == "non-wss"
          and os.path.getsize(os.path.join(root, e)) != 0]
    check("C15_nonwss_markers_are_empty", not nz, "%d non-empty" % len(nz))

    n_pass = sum(1 for _n, ok, _d in results if ok)
    n_fail = len(results) - n_pass
    print("SUMMARY checks=%d pass=%d fail=%d files=%d bytes=%d"
          % (len(results), n_pass, n_fail, len(entries), total))
    return 1 if n_fail else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: %s <packaged_galpol_dir>" % sys.argv[0])
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
