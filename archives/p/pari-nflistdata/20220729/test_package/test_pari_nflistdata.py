#!/usr/bin/env python3
"""nflistdata 载荷完整性验证器 — pari-nflistdata/20220729.

同一个脚本被两处复用（与同族 pari-galdata/pari-galpol 范式一致）：

  * `conanfile.build()`  —— `--source-root <src>`，校验 **解包后的上游树**，
    使损坏/被篡改的下载在 conan create 中途即失败；
  * `test_package.test()` —— `--package-root <pkg>`，校验 **打包产物**
    `<pkg>/res/pari/nflistdata`，即 R34 要求的"实质依赖被测包内容"。

基线指纹来源（三处独立锚定，全部可离线复算）：
  官方源 https://pari.math.u-bordeaux.fr/pub/pari/packages/nflistdata.tgz
    sha256 2c19a3e0…44bc，3623252 B，Last-Modified 2022-07-29（= 本包版本号）
  Debian pari-nflistdata_0.20220729-2.dsc Checksums-Sha256 同值
  采集方式：python3 <repo>/…/baseline-fingerprint.py <unpacked_work_dir>
    （按相对路径排序、依次拼接文件内容后取 sha256）

退出码：全部断言通过 0；任一失败 1（并打印失败项）。
"""

import hashlib
import os
import re
import sys

# ── 上游 20220729 发布物的基线指纹 ────────────────────────────────────────────
FILE_COUNT = 678
TOTAL_BYTES = 8845045

# 每度（群的次数）下的 QT 正则扩张表数量；合计 650
QT_PER_DEGREE = {
    2: 1, 3: 2, 4: 5, 5: 5, 6: 16, 7: 7, 8: 50, 9: 34,
    10: 45, 11: 8, 12: 301, 13: 9, 14: 63, 15: 104,
}
QT_COUNT = 650
QT_BYTES = 2587497

# A5 数域表（Jones–Roberts 与 Allombert–Page 两套 × 两种签名 × 分片）
A5_SHARDS = {
    "5/4/0": [str(i) for i in range(6)],        # JR, r2 = 0
    "5/4/0cond": [str(i) for i in range(10)],   # AP, r2 = 0，按 conductor 排序
    "5/4/2": ["0"],                             # JR, r2 = 2
    "5/4/2cond": [str(i) for i in range(10)],   # AP, r2 = 2，按 conductor 排序
}

# 分类拼接 sha256（按相对路径排序后拼接内容）
CLASS_SHA256 = {
    "ALL": "95e2e852d2e16bfb99f9be0a5b18bbfa9203c5baed2d005fcb61173f8702cd15",
    "QT": "ceafd56cb8d6f203c0e6f5d7b74d64621c2eec1baf0dc61a12547782f5dcd73d",
    "A5_r2_0": "328f76007a907066da6b04e6cb9cf1da0be967d422a1f1c5debe9b95c575be84",
    "A5_r2_0cond": "63ba2fe4011e863eae3e418bb32f25a055df74e45478d20525b836f0a16e238a",
    "A5_r2_2": "e85a26458ec706083b15bfe40c3eb3f6eaf569812e8db052465d804498e1a1a1",
    "A5_r2_2cond": "8b13c4dcfe55f875baa632793f06b686e90fdca492568ef6ab014d90c8db6628",
    "README": "2df162acb22119ef5593803ff0662ceed614c24998dc8ef9eedb50afaf124b44",
}
CLASS_BYTES = {
    "QT": QT_BYTES,
    "A5_r2_0": 507663,
    "A5_r2_0cond": 455711,
    "A5_r2_2": 61815,
    "A5_r2_2cond": 5230825,
    "README": 1534,
}

# 14 个单文件抽查（覆盖 README / 各度 QT / 全部四类 A5 分片首末）
SPOT_SHA256 = {
    "README": "2df162acb22119ef5593803ff0662ceed614c24998dc8ef9eedb50afaf124b44",
    "2/1/QT": "13476432341bc3e5244bc956c05f3f54ab1b99dedef85da3a7b834e509896bf4",
    "5/4/QT": "0745ed981ac0f830168f93bdf9ec58535fe2f14a7b7d535f208402b67cb27dd5",
    "8/1/QT": "6a37d8d42b0fad4c39f1ac43b79e262c8657f77d2c5339b5c076e0493a700b7d",
    "12/1/QT": "8ed0d58fd261aae4f42e87274fbdd99d1e7cff03f5571f3ea96c599866e75b02",
    "14/1/QT": "2cf9f69f65b4ddd38667a9a60fe0df592b84f581cc87b047902160b33751c513",
    "15/104/QT": "1436bc38cb1d65a0f58c425815c387b970dc86a88b549ecd3b1c9b906d9bc8c9",
    "5/4/0/0": "335071ac60160c70c305bce8c83d7efc5692101c79dcbc04749f848ffa8cbefe",
    "5/4/0/5": "3d708c40bc12a700ee6a3c291e0c693469c981e9c267f2f0fe46f875df81d37c",
    "5/4/0cond/0": "600480892f18f1cd24ee2b73fef9ab8d33d6222162dc7e56d35b53d04fa21b8a",
    "5/4/0cond/9": "583334464a382bf9536ee6c8e47053dfad9b1f0ed8caebe58298fcc3de317c66",
    "5/4/2/0": "e85a26458ec706083b15bfe40c3eb3f6eaf569812e8db052465d804498e1a1a1",
    "5/4/2cond/0": "dd1e3537aa568110e2762a0ea4abe0086d9acb9239b5a956227ca35c079d7404",
    "5/4/2cond/9": "33f812d6deeb27383a69544dfa355ca432ceecaba608161e8fd8bae6ac788c6e",
}

QT_RE = re.compile(rb"^\[[0-9,\[\]\-]+\]$")
# A5 表的行格式：数据行 `[[系数…],边界值]`；JR 表的**末分片**以哨兵行 `[0,0]`
# 标记表到此完备（实证：27 个 A5 文件中只有 5/4/0/5 与 5/4/2/0 含该哨兵）。
A5_LINE_RE = re.compile(rb"^\[\[[0-9,\-]+\],[0-9]+\]$")
A5_SENTINEL = b"[0,0]"
# 上游 README 声明的完备性边界：r2=0 disc ≤ 524286^2，r2=2 disc ≤ 10^8，
# 表内第二个字段存的是 sqrt(|disc|)，故末条分别为 524286 / 10000。
A5_JR_TAIL_BOUND = {"5/4/0/5": b"524286", "5/4/2/0": b"10000"}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def class_of(rel):
    if rel == "README":
        return "README"
    if rel.endswith("/QT"):
        return "QT"
    if rel.startswith("5/4/0cond/"):
        return "A5_r2_0cond"
    if rel.startswith("5/4/2cond/"):
        return "A5_r2_2cond"
    if rel.startswith("5/4/0/"):
        return "A5_r2_0"
    if rel.startswith("5/4/2/"):
        return "A5_r2_2"
    return "OTHER"


class Checker:
    def __init__(self, root):
        self.root = root
        self.passed = 0
        self.failed = 0
        self.names = []

    def check(self, name, ok, detail=""):
        self.names.append((name, "PASS" if ok else "FAIL"))
        if ok:
            self.passed += 1
        else:
            self.failed += 1
            print("FAIL %s %s" % (name, detail))

    def run(self):
        root = self.root
        if not os.path.isdir(root):
            print("FAIL tree_exists: %s 不存在" % root)
            return 1
        self.check("tree_exists", True)

        files = []
        for dirpath, _dirs, fns in os.walk(root):
            for fn in fns:
                files.append(os.path.relpath(
                    os.path.join(dirpath, fn), root).replace(os.sep, "/"))
        files.sort()

        self.check("file_count", len(files) == FILE_COUNT,
                   "found %d entries, expected %d" % (len(files), FILE_COUNT))
        total = sum(os.path.getsize(os.path.join(root, f)) for f in files)
        self.check("total_bytes", total == TOTAL_BYTES,
                   "found %d bytes, expected %d" % (total, TOTAL_BYTES))

        # 意外文件 / 空文件
        unexpected = [f for f in files if class_of(f) == "OTHER"]
        self.check("no_unexpected_files", not unexpected,
                   "unexpected: %s" % unexpected[:5])
        empties = [f for f in files
                   if os.path.getsize(os.path.join(root, f)) == 0]
        self.check("no_empty_files", not empties, "empty: %s" % empties[:5])

        # 度目录集合
        degrees = sorted({int(f.split("/")[0]) for f in files if f != "README"})
        self.check("degree_dirs",
                   degrees == sorted(QT_PER_DEGREE),
                   "found %s" % degrees)

        # 每度 QT 计数
        for deg in sorted(QT_PER_DEGREE):
            got = sum(1 for f in files
                      if f.endswith("/QT") and f.split("/")[0] == str(deg))
            self.check("qt_count_degree_%d" % deg, got == QT_PER_DEGREE[deg],
                       "found %d, expected %d" % (got, QT_PER_DEGREE[deg]))

        qt_total = sum(1 for f in files if f.endswith("/QT"))
        self.check("qt_count_total", qt_total == QT_COUNT,
                   "found %d, expected %d" % (qt_total, QT_COUNT))

        # A5 分片存在性（4 套表 × 各自分片编号连续）
        for prefix, shards in sorted(A5_SHARDS.items()):
            for sh in shards:
                rel = "%s/%s" % (prefix, sh)
                self.check("a5_shard_%s" % rel.replace("/", "_"),
                           rel in files, "missing %s" % rel)

        # 分类字节数与拼接 sha256
        by_class = {}
        for rel in files:
            by_class.setdefault(class_of(rel), []).append(rel)
        for cls, want in sorted(CLASS_BYTES.items()):
            got = sum(os.path.getsize(os.path.join(root, f))
                      for f in by_class.get(cls, []))
            self.check("class_bytes_%s" % cls, got == want,
                       "found %d, expected %d" % (got, want))
        for cls, want in sorted(CLASS_SHA256.items()):
            members = (files if cls == "ALL" else by_class.get(cls, []))
            h = hashlib.sha256()
            for rel in members:
                with open(os.path.join(root, rel), "rb") as fh:
                    h.update(fh.read())
            got = h.hexdigest()
            self.check("concat_sha256_%s" % cls, got == want,
                       "got %s expected %s" % (got, want))

        # 单文件抽查
        for rel, want in sorted(SPOT_SHA256.items()):
            p = os.path.join(root, rel)
            got = sha256_file(p) if os.path.isfile(p) else "<missing>"
            self.check("spot_sha256_%s" % rel.replace("/", "_").replace(".", "_"),
                       got == want, "got %s expected %s" % (got, want))

        # 内容语法全量校验
        bad_qt = []
        for rel in by_class.get("QT", []):
            with open(os.path.join(root, rel), "rb") as fh:
                body = fh.read()
            lines = body.rstrip(b"\n").split(b"\n")
            if len(lines) != 1 or not QT_RE.match(lines[0]):
                bad_qt.append(rel)
        self.check("qt_syntax_all", not bad_qt,
                   "%d malformed, e.g. %s" % (len(bad_qt), bad_qt[:3]))

        bad_a5 = []
        a5_files = [f for c in ("A5_r2_0", "A5_r2_0cond", "A5_r2_2",
                               "A5_r2_2cond") for f in by_class.get(c, [])]
        tails = {}
        for rel in a5_files:
            with open(os.path.join(root, rel), "rb") as fh:
                lines = [ln.rstrip(b"\n") for ln in fh if ln.strip()]
            tails[rel] = lines
            for ln in lines:
                if ln != A5_SENTINEL and not A5_LINE_RE.match(ln):
                    bad_a5.append("%s:%s" % (rel, ln[:24]))
                    break
        self.check("a5_table_syntax_all", not bad_a5,
                   "%d malformed, e.g. %s" % (len(bad_a5), bad_a5[:2]))

        # JR 表末分片的完备性哨兵（行内容 + 边界值，与上游 README 声明一致）
        for rel, bound in sorted(A5_JR_TAIL_BOUND.items()):
            lines = tails.get(rel, [])
            ok = (len(lines) >= 2 and lines[-1] == A5_SENTINEL
                  and lines[-2].endswith(b"," + bound + b"]"))
            self.check("a5_jr_sentinel_%s" % rel.replace("/", "_"), ok,
                       "tail=%r expected last=data[..,%s] then [0,0]"
                       % (lines[-2:], bound.decode()))

        # AP（按 conductor 排序）表不带哨兵：若出现即说明表结构与 pin 的基线不同
        cond_with_sentinel = [rel for rel in a5_files
                              if "cond" in rel and A5_SENTINEL in tails[rel]]
        self.check("a5_cond_tables_have_no_sentinel",
                   not cond_with_sentinel,
                   "unexpected sentinel in %s" % cond_with_sentinel[:3])

        # README 必须是 GP 生态 GPL 声明文本
        readme = os.path.join(root, "README")
        ok_readme = os.path.isfile(readme)
        if ok_readme:
            with open(readme, "r", encoding="utf-8", errors="replace") as fh:
                txt = fh.read()
            ok_readme = ("nflist" in txt and "GNU General Public License" in txt)
        self.check("readme_content", ok_readme, "README 缺少 nflist/GPL 声明")

        print("TOTAL=%d PASS=%d FAIL=%d" % (self.passed + self.failed,
                                            self.passed, self.failed))
        return 0 if self.failed == 0 else 1


def main(argv):
    if len(argv) != 3 or argv[1] not in ("--source-root", "--package-root"):
        print(__doc__)
        print("用法: %s --source-root <解包目录> | --package-root <包目录>" % argv[0])
        return 2
    arg, value = argv[1], argv[2]
    if arg == "--source-root":
        # init-build 的解包树 / conan strip_root 后的源码树根是 <root>/nflistdata
        root = os.path.join(value, "nflistdata")
        if not os.path.isdir(root):
            root = value
    else:
        root = os.path.join(value, "res", "pari", "nflistdata")
    print("mode=%s root=%s" % (arg, root))
    return Checker(root).run()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
