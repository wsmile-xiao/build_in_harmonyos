#!/usr/bin/env python3
"""kicad-symbols 消费者测试（适配新增，OHOS 侧真实消费被测包）。

上游 kicad-symbols 仓库自身不含任何测试程序：它把全部校验委托给**另一个仓库**
``kicad-library-utils``，由 ``.gitlab-ci.yml`` 的 ``klc-check`` 作业调用两个程序：

  1. ``klc-check/check_lib_table.py``  —— 符号库表 sym-lib-table 与库文件集合的一致性
  2. ``klc-check/comparelibs.py``      —— KLC（KiCad Library Convention）规则检查 +
                                          与上一版本对比（需要 git 历史 + kicad-footprints
                                          仓库，无法在离线 CI 中复现）

本测试以**自包含**方式复现 check_lib_table.py 的全部判定（检查名与上游一一对应：
Path separators / Incorrect nickname / Extra library / Duplicated library / Missing library /
Library table bad lines），并在其上补充 KLC 结构性检查与“KiCad 读取语义”检查：打包库必须
是完整且括号配平的 s-expression 文档、符号必须具备 Reference/Value 属性、已知经典器件必须
存在于预期库中且引脚数正确。仅依赖标准库，可直接在 OHOS CI worker 的 python3 上运行。

用法: test_kicad_symbols.py <package_folder>
"""
import os
import re
import sys

SYMBOLS_SUBDIR = os.path.join("share", "kicad", "symbols")
TABLE_SUBPATH = os.path.join("share", "kicad", "template", "sym-lib-table")

# KiCad 全局符号库表的占位符（上游 sym-lib-table 使用 ${KICAD10_SYMBOL_DIR}）
PLACEHOLDER_RE = re.compile(r"\$\{[A-Za-z0-9_]+\}")

# 已知经典器件：(库, 符号名, 期望引脚数)。引脚数为该版本实测的确定值
# （源码由 sha256 固定，故可精确断言）：
#   Device:R / Device:C   2  |  power:GND  1
#   74xx:74LS00          26 —— 该符号声明 (body_styles demorgan)，每个 unit 有两套
#                        body style 各含一份引脚，故 4 门×3 引脚×2 + 电源单元 2 = 26
KNOWN_SYMBOLS = [
    ("Device", "R", 2),
    ("Device", "C", 2),
    ("power", "GND", 1),
    ("74xx", "74LS00", 26),
]

_RE_LIB_LINE = re.compile(r"\(lib\s")
_RE_NAME = re.compile(r'\(name "?([^)"]*)"?\)')
_RE_TYPE = re.compile(r'\(type "?([^)"]*)"?\)')
_RE_URI = re.compile(r'\(uri "?([^)"]*)"?\)')
_RE_OPTIONS = re.compile(r'\(options "?([^)"]*)"?\)')
_RE_DESCR = re.compile(r'\(descr "?([^)"]*)"?')


class Checker:
    """极简断言收集器：逐条记录 PASS/FAIL，最后统一给退出码。"""

    def __init__(self, name):
        self.name = name
        self.passed = 0
        self.failed = 0

    def check(self, ok, label, detail=""):
        if ok:
            self.passed += 1
            print("  [OK]   %s%s" % (label, (" — " + detail) if detail else ""))
        else:
            self.failed += 1
            print("  [FAIL] %s%s" % (label, (" — " + detail) if detail else ""))
        return ok

    def report(self):
        total = self.passed + self.failed
        print("\n%s: %d/%d assertions passed" % (self.name, self.passed, total))
        return self.failed == 0


def sexpr_depth_ok(text):
    """引号感知的括号配平检查（属性字符串中可能含括号，不能简单计数）。"""
    depth = 0
    in_str = False
    i = 0
    while i < len(text):
        ch = text[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return False
        i += 1
    return depth == 0


def extract_block(text, open_idx):
    """返回 text[open_idx] 处 '(' 起始的、括号配平的完整子串。"""
    depth = 0
    in_str = False
    i = open_idx
    while i < len(text):
        ch = text[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[open_idx:i + 1]
        i += 1
    return None


def parse_lib_table(path):
    """解析 sym-lib-table —— 与上游 common/lib_table.py 的解析口径一致。"""
    entries = []
    bad_lines = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            if not _RE_LIB_LINE.search(line):
                continue
            name = _RE_NAME.search(line)
            ltype = _RE_TYPE.search(line)
            uri = _RE_URI.search(line)
            options = _RE_OPTIONS.search(line)
            descr = _RE_DESCR.search(line)
            if name and ltype and uri and options and descr:
                entries.append({
                    "name": name.group(1),
                    "type": ltype.group(1),
                    "uri": uri.group(1),
                    "options": options.group(1),
                    "descr": descr.group(1),
                })
            else:
                bad_lines.append(line.rstrip())
    return entries, bad_lines


def main():
    pkg_root = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PACKAGE_ROOT", "")
    if not pkg_root or not os.path.isdir(pkg_root):
        print("ERROR: package folder not given or not a directory: %r" % pkg_root,
              file=sys.stderr)
        return 2

    # 只读包目录（Conan 缓存/HMDFS 上可能不可写），全程只读不写
    symbols_dir = os.path.join(pkg_root, SYMBOLS_SUBDIR)
    table_path = os.path.join(pkg_root, TABLE_SUBPATH)

    ck = Checker("kicad-symbols consumer test")

    # ── 1. 安装布局（与 Debian 官方 kicad-symbols 包同构） ──────────────────
    print("[1] installed layout")
    ck.check(os.path.isdir(symbols_dir), "share/kicad/symbols exists", symbols_dir)
    ck.check(os.path.isfile(table_path), "share/kicad/template/sym-lib-table exists")
    ck.check(os.path.isfile(os.path.join(pkg_root, "licenses", "LICENSE.md")),
             "licenses/LICENSE.md shipped")
    if not (os.path.isdir(symbols_dir) and os.path.isfile(table_path)):
        print("\nRESULT: FAILED (package layout incomplete)")
        return 1

    lib_files = sorted(f for f in os.listdir(symbols_dir) if f.endswith(".kicad_sym"))
    sim_files = sorted(f for f in os.listdir(symbols_dir) if f.endswith(".sp"))
    ck.check(len(lib_files) > 200, "packed symbol libraries present", "%d libs" % len(lib_files))
    ck.check(sim_files == ["Simulation_SPICE.sp"],
             "Simulation_SPICE.sp installed", ", ".join(sim_files))

    entries, bad_lines = parse_lib_table(table_path)

    # ── 2. 上游 check_lib_table.py 的判定（逐条等价复现） ───────────────────
    print("[2] upstream check_lib_table.py checks")
    ck.check(len(entries) > 200, "table parsed", "%d entries" % len(entries))

    # "Library table bad lines"
    ck.check(not bad_lines, "Library table bad lines",
             "%d unparsable (lib ...) lines" % len(bad_lines))

    # "Path separators"
    ck.check(all("\\" not in e["uri"] for e in entries), "Path separators")

    # "Incorrect nickname"：uri 去掉最后一段扩展名后必须等于 nickname
    mismatch = [e["name"] for e in entries
                if ".".join(e["uri"].split("/")[-1].split(".")[:-1]) != e["name"]]
    ck.check(not mismatch, "Incorrect nickname",
             ", ".join(mismatch[:5]) if mismatch else "")

    # 打包后的库表必须指向打包后的库（上游 kicad_lib_pack.py --table 的改写结果）
    not_packed = [e["name"] for e in entries if not e["uri"].endswith(".kicad_sym")]
    ck.check(not not_packed, "all table uris point at packed .kicad_sym",
             ", ".join(not_packed[:5]) if not_packed else "")

    table_names = [e["name"] for e in entries]
    installed_names = [f[: -len(".kicad_sym")] for f in lib_files]

    # "Extra library"
    extra = sorted(set(table_names) - set(installed_names))
    ck.check(not extra, "Extra library", ", ".join(extra[:5]) if extra else "")

    # "Missing library"
    missing = sorted(set(installed_names) - set(table_names))
    ck.check(not missing, "Missing library", ", ".join(missing[:5]) if missing else "")

    # "Duplicated library"
    dup = sorted(n for n in set(table_names) if table_names.count(n) > 1)
    ck.check(not dup, "Duplicated library", ", ".join(dup[:5]) if dup else "")

    # 表项 uri 必须能解析到包内真实文件：把 ${KICAD10_SYMBOL_DIR} 解析为包内 symbols 目录
    # （KiCad 运行时即用该环境变量指向 share/kicad/symbols）
    unresolved = []
    for e in entries:
        resolved = PLACEHOLDER_RE.sub(symbols_dir.replace("\\", "/"), e["uri"])
        if not os.path.isfile(resolved):
            unresolved.append(e["name"])
    ck.check(not unresolved, "Every table uri resolves inside the package",
             ", ".join(unresolved[:5]) if unresolved else "")

    # ── 3. 结构完整性（KLC 派生：库文件必须是完整的 s-expression 文档） ─────
    print("[3] packed library structural integrity")
    header_bad, paren_bad, empty_lib = [], [], []
    total_symbols = 0
    for fname in lib_files:
        with open(os.path.join(symbols_dir, fname), "r", encoding="utf-8") as fh:
            text = fh.read()
        if not text.lstrip().startswith("(kicad_symbol_lib"):
            header_bad.append(fname)
        if not sexpr_depth_ok(text):
            paren_bad.append(fname)
        n_sym = len(re.findall(r'\n\t\(symbol "', text))
        total_symbols += n_sym
        if n_sym == 0:
            empty_lib.append(fname)
    ck.check(not header_bad, "every library has (kicad_symbol_lib ...) header",
             ", ".join(header_bad[:5]) if header_bad else "")
    ck.check(not paren_bad, "every library has balanced parentheses (quote-aware)",
             ", ".join(paren_bad[:5]) if paren_bad else "")
    ck.check(not empty_lib, "no empty library",
             ", ".join(empty_lib[:5]) if empty_lib else "")
    ck.check(total_symbols > 20000, "total symbol count", "%d symbols" % total_symbols)

    # ── 4. KiCad 读取语义：已知器件存在、属性齐备、引脚数正确 ───────────────
    print("[4] KiCad consumption semantics")
    by_name = dict(zip(installed_names, lib_files))
    for lib, sym, pins in KNOWN_SYMBOLS:
        fname = by_name.get(lib)
        if not fname:
            ck.check(False, "library %s installed" % lib)
            continue
        with open(os.path.join(symbols_dir, fname), "r", encoding="utf-8") as fh:
            text = fh.read()
        m = re.search(r'\(symbol "%s"\s' % re.escape(sym), text)
        block = extract_block(text, m.start()) if m else None
        if not block:
            ck.check(False, "%s:%s present" % (lib, sym))
            continue
        has_ref = '(property "Reference"' in block
        has_val = '(property "Value"' in block
        n_pins = len(re.findall(r"\(pin\s", block))
        ck.check(has_ref and has_val,
                 "%s:%s has Reference/Value properties" % (lib, sym))
        ck.check(n_pins == pins,
                 "%s:%s pin count" % (lib, sym),
                 "expected %d, found %d" % (pins, n_pins))

    ok = ck.report()
    print("\nRESULT: %s" % ("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
