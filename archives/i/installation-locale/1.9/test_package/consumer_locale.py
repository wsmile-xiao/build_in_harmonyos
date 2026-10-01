#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""installation-locale 1.9 —— 完整消费者用例（平台 rule12：端到端跑通真实功能）

本脚本不是一个"断言集合"，而是一个**真正的消费者**：它像 glibc 的 `localedef`
那样把交付的 locale 定义源读进来、建成字符类别/大小写映射表，然后**用这些表去
处理真实文本**，并给出可核对的数值结果。

消费链路（每一步都读真实数据、产出真实数值）:

  1. 交付物契约        <pkg>/share/i18n/locales/C.UTF-8.in（与 Debian/glibc 的
                       /usr/share/i18n/locales/ 同形，即 localedef 的
                       `I18NPATH/locales/<name>` 查找路径）
  2. localedef 等价解析  按 POSIX/glibc locale 定义语法读：comment_char/escape_char
                       与行续接、12 个 LC_* 类别、`copy "..."` 类别引用、
                       `<Uxxxx>` / `<Uxxxx>..<Uyyyy>` / `<Uxxxx>..(N)..<Uyyyy>`
                       区间、`(a,b)` 映射对、`class "..."` / `map "..."` 具名块，
                       以及 glibc 生成器留下的 `<0>` 占位符（见 notes.md：把
                       `<0>;` 删掉后 localedef 编译出的 LC_CTYPE **逐字节相同**，
                       即它不贡献任何码位）。
  3. LC_CTYPE 表重建    11 个字符类别（upper/lower/alpha/digit/space/cntrl/punct/
                       graph/print/xdigit/blank）+ 3 个映射（toupper/tolower/
                       totitle）+ 2 个具名类（combining/combining_level3）。
  4. 真实查询           "某个字符属于哪些类别"、"某个 locale 类别的定义是什么"、
                       "某个码位的大写/小写是什么"。
  5. 端到端文本处理     用**交付的表**跑一遍真实的 locale 相关文本流水线：
                       逐码位分类 → 按 blank 类切词 → 用交付的 toupper 映射折叠
                       大小写 → 产出计数与指纹。
  6. 独立 oracle 交叉核对
                       (a) **上游参考实现**：GNU libc 2.43 的 `localedef` 编译本
                           文件后由 `iswctype()`/`towupper()`/`towlower()`/
                           `towctrans()` 报出的类别规模与映射规模（GOLDEN_*），
                           本脚本的纯 Python 重建必须逐项一致；
                       (b) **ISO C 强制项**：xdigit 必须恰为 0-9A-Fa-f，blank 必须
                           含 TAB/SPACE，ASCII 段 upper/lower 必须恰为 A-Z / a-z；
                       (c) **Python 独立实现**：ASCII 与 Latin-1 段的大小写映射必须
                           与 `unicodedata` 逐项一致（与 glibc 完全独立的第二实现），
                           并**如实记录** Unicode 3.2（2005 年 glibc 数据）与新版
                           unicodedata 之间的版本落差。

用法: python3 consumer_locale.py <package_folder> [--report]
      --report 只打印可钉死的数值（供人工核对/更新 GOLDEN_*），不做判定。
退出码：0 = 全部通过；1 = 有失败项。
"""
from __future__ import print_function

import hashlib
import os
import re
import sys

# ── 交付物契约 ────────────────────────────────────────────────────────────────
LOCALE_REL = os.path.join("share", "i18n", "locales", "C.UTF-8.in")
PAYLOAD_SHA256 = "af4b0dad56d6e3426ea4da0110aa4a330d489e3ebdeb6d8f5fb393c21ca137c2"
PAYLOAD_BYTES = 81642
PAYLOAD_LINES = 1410

# ── 上游参考实现参照值（GNU libc） ────────────────────────────────────────────
# 生成方式（本机 Ubuntu / GNU libc 2.43）：
#   localedef --no-archive -i <交付的 C.UTF-8.in> -f UTF-8 ./loc/C.UTF-8
#   LOCPATH=./loc LC_ALL=C.UTF-8 <probe: iswctype()/towupper()/towlower()/
#                                        towctrans(wctrans("totitle"))>
# 即"**上游参考实现**读同一份交付数据后报出的结果"，与下面的纯 Python 重建互为
# 独立实现。alnum 由 glibc 自动合成（alpha ∪ digit），文件里没有显式定义，
# 故单独列出。
GOLDEN_CLASS_COUNTS = {
    "upper": 749,
    "lower": 760,
    "alpha": 90342,
    "digit": 10,
    "xdigit": 22,
    "space": 22,
    "print": 232622,
    "graph": 232607,
    "blank": 16,
    "cntrl": 67,
    "punct": 142253,
    "alnum": 90352,
    "combining": 669,
    "combining_level3": 431,
}
GOLDEN_MAP_CHANGES = {"toupper": 759, "tolower": 749, "totitle": 759}
# `locale -k LC_CTYPE` 报出的类别名/映射名（上游参考实现口径）
GOLDEN_CTYPE_CLASS_NAMES = (
    "upper", "lower", "alpha", "digit", "xdigit", "space", "print", "graph",
    "blank", "cntrl", "punct", "alnum", "combining", "combining_level3")
GOLDEN_CTYPE_MAP_NAMES = ("toupper", "tolower", "totitle")
# 文件里 11 个字符类别块的出现顺序（不含 glibc 合成的 alnum）
GOLDEN_FILE_CLASS_ORDER = (
    "upper", "lower", "alpha", "digit", "space", "cntrl", "punct", "graph",
    "print", "xdigit", "blank", "combining", "combining_level3")
# (码位, 期望属于的类别集合)，逐项由上述 glibc 探针产生
GOLDEN_PROBES = (
    (0x0030, {"print", "graph", "xdigit", "digit", "alnum"}),   # '0'
    (0x0047, {"print", "graph", "alpha", "upper", "alnum"}),  # 'G'
    (0x0067, {"print", "graph", "alpha", "lower", "alnum"}),  # 'g'
    (0x00E9, {"print", "graph", "alpha", "lower", "alnum"}),  # 'é'
    (0x00A0, {"print", "graph", "punct"}),                    # NBSP
    (0x0009, {"blank", "space", "cntrl"}),                    # TAB
    (0x0020, {"print", "blank", "space"}),                    # SPACE
    (0x3000, {"print", "blank", "space"}),                    # 全角空格
    (0x200B, {"print", "blank", "space"}),                    # 零宽空格
    (0x007F, {"cntrl"}),                                      # DEL
    (0x4E00, {"print", "graph", "alpha", "alnum"}),           # 一
    (0xFF01, {"print", "graph", "punct"}),                    # ！
    (0x00B5, {"print", "graph", "alpha", "lower", "alnum"}),  # µ
    (0x1F600, set()),                                         # emoji：Unicode 3.2 未分配
)
# (码位, toupper 结果, tolower 结果) —— 上游参考实现 towupper/towlower
GOLDEN_CASE_PROBES = (
    (0x0061, 0x0041, 0x0061),      # a -> A
    (0x00E9, 0x00C9, 0x00E9),      # é -> É
    (0x00B5, 0x039C, 0x00B5),      # µ -> Μ（非互逆：tolower(Μ)=μ 而不是 µ）
    (0x017F, 0x0053, 0x017F),      # ſ -> S
    (0x0131, 0x0049, 0x0131),      # ı -> I
    (0x0345, 0x0399, 0x0345),      # 组合用 ypogegrammeni -> Ι
    (0x1E9B, 0x1E60, 0x1E9B),      # ẛ -> Ṡ
    (0x10428, 0x10400, 0x10428),   # 德撒律小写 -> 大写（补充平面）
)
# 交付数据里"把大写映射回来不等于原字符"的对数（Unicode 事实，不是缺陷）
GOLDEN_NON_RECIPROCAL = 19
# 与新版 unicodedata 不一致的非 ASCII 大小写对数（Unicode 3.2 版本落差）
GOLDEN_UNICODE_DRIFT = 28

# ── 端到端文本处理用的真实语料（混合拉丁/希腊/西里尔/中日韩、控制与空白、
#    非互逆大小写对、补充平面字符、以及 Unicode 3.2 未分配的 emoji） ──────────
CORPUS = (
    "Debian installer locale test\n",
    "Wähle eine Sprache: Deutsch / Sprache\n",
    "Ελληνικά Πληκτρολόγιο\n",
    "Русский: Раскладка клавиатуры\n",
    "日本語のフォント 中文 字体\n",
    "ID\t0x1F600\u00a0\u3000\u200b\u1680\n",
    "digits 0123456789 xdigit ABCDEFabcdef\n",
    "\u00b5 \u017f \u0131 \u0345 \u1e9b\n",
    "\U00010428\U0001D400\U0001F600\n",
)
# 上述语料的处理结果（由交付数据本身决定；数据一改即失败）
GOLDEN_CORPUS_CODEPOINTS = 201
GOLDEN_CORPUS_BLANKS = 24
GOLDEN_CORPUS_TOKENS = 30
GOLDEN_CORPUS_FOLDED = 117
GOLDEN_CORPUS_CLASS_HITS = {
    "upper": 18, "lower": 117, "alpha": 148, "digit": 15, "xdigit": 53,
    "space": 33, "print": 190, "graph": 167, "blank": 24, "cntrl": 10,
    "punct": 4, "alnum": 163, "combining": 1, "combining_level3": 0,
}
GOLDEN_CORPUS_DIGEST = "17742499d7cfb82d2db796e7f5ab13930824fdb8e66357275530cd51c7384f68"

# ── localedef 等价读取器 ─────────────────────────────────────────────────────
_COMMENT = "%"
_ESCAPE = "/"
_DIRECTIVE = re.compile(r"^(escape_char|comment_char)\s+(\S)$")
_SECTION = re.compile(r"^LC_([A-Z_]+)$")
_END_SECTION = re.compile(r"^END LC_([A-Z_]+)$")
_BLOCK = re.compile(r'^(class|map)\s+"([A-Za-z0-9_]+)"$')
_IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")
_COPY = re.compile(r'^copy\s+"([^"]+)"$')
_RANGE = re.compile(r"^<U([0-9A-Fa-f]{4,8})>(?:\.\.(?:\((\d+)\)\.\.)?<U([0-9A-Fa-f]{4,8})>)?$")
_PAIR = re.compile(r"^\(\s*<U([0-9A-Fa-f]{4,8})>\s*,\s*<U([0-9A-Fa-f]{4,8})>\s*\)$")
# glibc 的 gen-unicode-ctype.c 在"该数字集的零不存在"处写出的占位符。
_PLACEHOLDER = re.compile(r"^<0>$")


class LocaleSyntaxError(ValueError):
    """locale 定义源里出现了本读取器无法解释的语法。"""


def _logical_lines(text):
    """去掉注释行与指令行，然后按 escape_char 续接合并成逻辑行。"""
    out, buf = [], ""
    for line in text.replace("\r\n", "\n").split("\n"):
        line = line.rstrip()
        if line.startswith(_COMMENT) or _DIRECTIVE.match(line):
            continue
        if line.endswith(_ESCAPE):
            buf += line[:-1]
            continue
        buf += line
        if buf.strip():
            out.append(buf.strip())
        buf = ""
    if buf.strip():
        out.append(buf.strip())
    return out


def read_definition(text):
    """按 localedef 的读法把定义源切成 {类别: [语句, ...]}。"""
    sections, cur = {}, None
    for line in _logical_lines(text):
        m = _SECTION.match(line)
        if m:
            cur = "LC_" + m.group(1)
            sections[cur] = []
            continue
        if _END_SECTION.match(line):
            cur = None
            continue
        if cur is None:
            continue                    # 文件头部的 comment_char/escape_char 声明
        for stmt in line.split(";"):
            stmt = " ".join(stmt.split())
            if stmt:
                sections[cur].append(stmt)
    return sections


def _expand_ranges(tokens):
    """`<U..>` / `<U..>..<U..>` / `<U..>..(N)..<U..>` → [(lo, hi, step), ...]。"""
    spans = []
    for token in tokens:
        if _PLACEHOLDER.match(token):
            continue
        m = _RANGE.match(token)
        if not m:
            raise LocaleSyntaxError("unparsable class entry: %r" % token)
        lo = int(m.group(1), 16)
        step = int(m.group(2)) if m.group(2) else 1
        hi = int(m.group(3), 16) if m.group(3) else lo
        spans.append((lo, hi, step))
    return spans


def _spans_to_set(spans):
    out = set()
    for lo, hi, step in spans:
        for cp in range(lo, hi + 1, step):
            if 0xD800 <= cp <= 0xDFFF:      # 代理区不是合法码位
                continue
            out.add(cp)
    return out


def parse_ctype(statements):
    """LC_CTYPE → ({类别: 码位集合}, {映射: {源: 目标}}, 类别块出现顺序)。

    localedef 的 LC_CTYPE 语法里，一个具名块由一个"块头"语句开场，其后到下一个
    块头之前的语句都是该块的条目：

        upper /                        -> 语句 "upper <U0041>..<U005A>"
           <U0041>..<U005A>;/             （块头与首个条目同句）
        class "combining"; /           -> 语句 'class "combining"'
           <U0300>..<U034F>;/             （块头独占一句）
        map "totitle"; /               -> 语句 'map "totitle"'
           (<U0061>,<U0041>);             （条目是 (a,b) 对）

    类别块的条目是码位区间，映射块的条目是 `(<Uxxxx>,<Uyyyy>)` 对；没有 `class`
    /`map` 关键字的块头（upper/lower/…/toupper/tolower）按首个条目的形态判别。
    """
    raw_classes, raw_maps, order = {}, {}, []
    block = kind = None
    for stmt in statements:
        parts = stmt.split()
        head = parts[0]
        m = _BLOCK.match(stmt)
        if m:                                       # class "x"; / map "y";
            kind, block = m.group(1), m.group(2)
            entries = parts[2:]                     # 跳过关键字与带引号的名字
            target = raw_classes if kind == "class" else raw_maps
            if block not in target:
                target[block] = []
                if kind == "class":
                    order.append(block)
        elif _IDENT.match(head):
            # 无关键字的块头：条目形如 (a,b) 的是映射，否则是类别
            kind = "map" if len(parts) > 1 and _PAIR.match(parts[1]) else "class"
            block = head
            entries = parts[1:]                     # 块头与首个条目同句
            target = raw_classes if kind == "class" else raw_maps
            if block not in target:
                target[block] = []
                if kind == "class":
                    order.append(block)
        else:
            if block is None:
                raise LocaleSyntaxError("entry without a block header: %r" % stmt)
            entries = parts                         # 续接条目：整句都是条目
        if kind == "class":
            raw_classes[block].extend(_expand_ranges(entries))
        else:
            for token in entries:
                pm = _PAIR.match(token)
                if not pm:
                    raise LocaleSyntaxError("unparsable map entry: %r" % token)
                raw_maps[block].append(
                    (int(pm.group(1), 16), int(pm.group(2), 16)))
    classes = {name: _spans_to_set(spans) for name, spans in raw_classes.items()}
    maps = {name: dict(pairs) for name, pairs in raw_maps.items()}
    return classes, maps, order


def category_definitions(sections):
    """每个类别名的定义：`copy "X"` 引用，或 inline。"""
    out = {}
    for name, stmts in sections.items():
        copies = [m.group(1) for s in stmts for m in [_COPY.match(s)] if m]
        out[name] = copies[0] if copies else "inline"
    return out


def classify(classes, cp):
    """某个码位落在哪些类别里。"""
    return frozenset(name for name, members in classes.items() if cp in members)


def corpus_codepoints():
    return [ord(ch) for line in CORPUS for ch in line]


def tokenize(classes, cps):
    """按交付的 blank 类切词：blank 与换行都是分隔符，其余码位原样保留。"""
    separated = "".join("\n" if cp in classes["blank"] else chr(cp) for cp in cps)
    return [tok for tok in separated.split("\n") if tok]


# ── 检查器 ───────────────────────────────────────────────────────────────────
_RESULTS = []


def check(ok, label, detail=""):
    _RESULTS.append((bool(ok), label))
    print("  [%s] %s%s" % ("ok" if ok else "FAIL", label,
                           ("  " + detail) if detail else ""))
    return bool(ok)


def eq(actual, expected, label):
    detail = "" if actual == expected else "actual=%r expected=%r" % (actual, expected)
    return check(actual == expected, label, detail)


def report(pkg):
    """--report：打印所有可钉死的数值，供人工核对/更新 GOLDEN_*。"""
    text = open(os.path.join(pkg, LOCALE_REL), encoding="utf-8").read()
    sections = read_definition(text)
    classes, maps, order = parse_ctype(sections["LC_CTYPE"])
    classes["alnum"] = classes["alpha"] | classes["digit"]
    print("file class order: %r" % (order,))
    for name in sorted(classes):
        print("class %-18s %d" % (name, len(classes[name])))
    for name in sorted(maps):
        print("map %-18s changes=%d pairs=%d"
              % (name, sum(1 for a, b in maps[name].items() if a != b), len(maps[name])))
    print("category definitions: %r" % (category_definitions(sections),))
    cps = corpus_codepoints()
    hits = {}
    for name in sorted(classes):
        hits[name] = sum(1 for cp in cps if cp in classes[name])
    upper = maps["toupper"]
    print("corpus: codepoints=%d blanks=%d tokens=%d folded=%d"
          % (len(cps),
             sum(1 for cp in cps if cp in classes["blank"]),
             len(tokenize(classes, cps)),
             sum(1 for cp in cps if upper.get(cp, cp) != cp)))
    print("corpus class hits: %r" % (hits,))
    digest = hashlib.sha256()
    for cp in cps:
        digest.update(("%04X:%s\n" % (cp, ",".join(sorted(classify(classes, cp))))).encode())
    print("corpus digest: %s" % digest.hexdigest())
    for label, limit in (("ascii(<0x80)", 0x80), ("latin1(<0x100)", 0x100),
                         ("all", 0x110000)):
        up = [(a, b) for a, b in maps["toupper"].items() if a < limit]
        lo = [(a, b) for a, b in maps["tolower"].items() if a < limit]
        print("unicodedata agreement [%s]: toupper %d/%d, tolower %d/%d"
              % (label, sum(1 for a, b in up if chr(a).upper() == chr(b)), len(up),
                 sum(1 for a, b in lo if chr(a).lower() == chr(b)), len(lo)))
    print("non-reciprocal toupper pairs: %d"
          % sum(1 for a, b in maps["toupper"].items() if maps["tolower"].get(b) != a))
    print("payload is pure ASCII: %s" % text.isascii())
    return 0


def main(argv):
    pkg = argv[1]
    src = os.path.join(pkg, LOCALE_REL)
    print("消费者用例（rule12）: %s" % src)

    print("\n[1] 交付物契约与本体校验")
    if not check(os.path.isfile(src),
                 "%s 存在（glibc localedef 的 I18NPATH/locales 约定路径）" % LOCALE_REL):
        return 1
    with open(src, "rb") as handle:
        raw = handle.read()
    text = raw.decode("utf-8")
    eq(len(raw), PAYLOAD_BYTES, "locale 定义源字节数 == %d" % PAYLOAD_BYTES)
    eq(hashlib.sha256(raw).hexdigest(), PAYLOAD_SHA256,
       "locale 定义源 sha256 与钉死值一致")
    eq(raw.count(b"\n"), PAYLOAD_LINES, "行数 == %d" % PAYLOAD_LINES)
    check(text.isascii(), "定义源是纯 ASCII（码位以 <Uxxxx> 记法书写，便于跨工具链搬运）")

    print("\n[2] localedef 等价解析（类别/引用/区间/映射）")
    sections = read_definition(text)
    expected_sections = ["LC_IDENTIFICATION", "LC_COLLATE", "LC_MESSAGES", "LC_NUMERIC",
                         "LC_TIME", "LC_ADDRESS", "LC_CTYPE", "LC_MEASUREMENT",
                         "LC_MONETARY", "LC_NAME", "LC_PAPER", "LC_TELEPHONE"]
    eq(sorted(sections), sorted(expected_sections), "12 个 LC_* 类别齐备且无多余")
    definitions = category_definitions(sections)
    golden_copy = {"LC_COLLATE": "POSIX", "LC_MESSAGES": "POSIX", "LC_NUMERIC": "POSIX",
                   "LC_TIME": "POSIX", "LC_ADDRESS": "i18n", "LC_MEASUREMENT": "i18n",
                   "LC_MONETARY": "i18n", "LC_NAME": "i18n", "LC_PAPER": "i18n",
                   "LC_TELEPHONE": "i18n", "LC_CTYPE": "inline",
                   "LC_IDENTIFICATION": "inline"}
    eq(definitions, golden_copy,
       '各 locale 类别的定义来源（copy "POSIX"/"i18n" 或 inline）')
    ident = " ".join(sections["LC_IDENTIFICATION"])
    eq(ident.count('category "i18n:2012"'), 11,
       "LC_IDENTIFICATION 声明 11 条 i18n:2012 类别")
    check('title "POSIX/i18n locale for UTF-8"' in ident,
          "LC_IDENTIFICATION 标题与上游一致")

    print("\n[3] LC_CTYPE 表重建 vs 上游参考实现（GNU libc localedef + isw*/tow*）")
    classes, maps, order = parse_ctype(sections["LC_CTYPE"])
    eq(order, list(GOLDEN_FILE_CLASS_ORDER), "具名类别块的出现顺序（含 2 个具名类）")
    eq(sorted(maps), ["tolower", "totitle", "toupper"], "3 个映射（toupper/tolower/totitle）")
    classes["alnum"] = classes["alpha"] | classes["digit"]   # glibc 自动合成
    eq(sorted(classes), sorted(GOLDEN_CTYPE_CLASS_NAMES),
       "类别名集合与 `locale -k LC_CTYPE` 报出的一致")
    eq(sorted(maps), sorted(GOLDEN_CTYPE_MAP_NAMES),
       "映射名集合与 `locale -k LC_CTYPE` 报出的一致")
    for name in sorted(GOLDEN_CLASS_COUNTS):
        eq(len(classes[name]), GOLDEN_CLASS_COUNTS[name],
           "类别 %s 的码位规模 == %d" % (name, GOLDEN_CLASS_COUNTS[name]))
    for name in sorted(GOLDEN_MAP_CHANGES):
        eq(sum(1 for a, b in maps[name].items() if a != b), GOLDEN_MAP_CHANGES[name],
           "映射 %s 实际改变映射关系的码位 == %d" % (name, GOLDEN_MAP_CHANGES[name]))

    print("\n[4] 真实查询（字符 → 类别；类别 → 定义；码位 → 大小写）")
    for cp, expected in GOLDEN_PROBES:
        eq(set(classify(classes, cp)), expected, "U+%04X 的类别归属" % cp)
    eq(definitions["LC_CTYPE"], "inline",
       '查询"LC_CTYPE 的定义" → 本文件 inline 定义')
    eq(definitions["LC_MONETARY"], "i18n",
       '查询"LC_MONETARY 的定义" → copy "i18n"')
    for cp, up, lo in GOLDEN_CASE_PROBES:
        eq(maps["toupper"].get(cp, cp), up, "toupper(U+%04X) == U+%04X" % (cp, up))
        eq(maps["tolower"].get(cp, cp), lo, "tolower(U+%04X) == U+%04X" % (cp, lo))

    print("\n[5] 端到端文本处理（用交付的表处理真实语料）")
    cps = corpus_codepoints()
    eq(len(cps), GOLDEN_CORPUS_CODEPOINTS, "语料码位总数")
    hits = {name: sum(1 for cp in cps if cp in classes[name])
            for name in sorted(GOLDEN_CORPUS_CLASS_HITS)}
    eq(hits, GOLDEN_CORPUS_CLASS_HITS, "语料在各交付类别下的命中数（逐类别）")
    blanks = [cp for cp in cps if cp in classes["blank"]]
    eq(len(blanks), GOLDEN_CORPUS_BLANKS, "按交付的 blank 类识别出的空白分隔符数")
    tokens = tokenize(classes, cps)
    eq(len(tokens), GOLDEN_CORPUS_TOKENS, "按 blank 类切词得到的 token 数")
    preserved = "".join(chr(cp) for cp in cps
                        if cp not in classes["blank"] and cp != 0x0A)
    eq("".join(tokens), preserved, "切词不丢码位（非 blank/换行的码位原样保留）")
    upper = maps["toupper"]
    folded = [upper.get(cp, cp) for cp in cps]
    eq(sum(1 for a, b in zip(cps, folded) if a != b), GOLDEN_CORPUS_FOLDED,
       "经交付的 toupper 映射发生改变的码位数")
    eq(len(folded), len(cps), "大小写折叠不改变码位个数（1:1 映射）")
    eq([upper.get(cp, cp) for cp in folded], folded, "toupper 映射幂等（再折叠一次不变）")
    eq(upper.get(0x10428, 0x10428), 0x10400,
       "补充平面大小写对 U+10428 → U+10400（真实折叠，不是恒等）")
    digest = hashlib.sha256()
    for cp in cps:
        digest.update(("%04X:%s\n" % (cp, ",".join(sorted(classify(classes, cp))))).encode())
    eq(digest.hexdigest(), GOLDEN_CORPUS_DIGEST, "语料分类结果指纹（sha256）")

    print("\n[6] 独立 oracle 交叉核对")
    # (b) ISO C / POSIX 强制项
    ascii_hex = sorted(list(range(0x30, 0x3A)) + list(range(0x41, 0x47)) +
                       list(range(0x61, 0x67)))
    eq(sorted(classes["xdigit"]), ascii_hex, "xdigit 恰为 ISO C 强制的 0-9A-Fa-f（22 个码位）")
    check(0x09 in classes["blank"] and 0x20 in classes["blank"],
          "blank 含 TAB 与 SPACE（POSIX 对 blank 的最小要求）")
    check(sorted(cp for cp in classes["upper"] if cp < 0x80) == list(range(0x41, 0x5B))
          and sorted(cp for cp in classes["lower"] if cp < 0x80) == list(range(0x61, 0x7B)),
          "ASCII 段 upper/lower 恰为 A-Z / a-z")
    eq(sorted(cp for cp in classes["digit"]), list(range(0x30, 0x3A)),
       "digit 恰为 ASCII 0-9（与 glibc iswdigit 一致）")
    check(all(cp not in classes["alpha"] for cp in range(0x30, 0x3A)),
          "ASCII 数字不属于 alpha（与 glibc iswalpha 一致）")
    eq(classes["blank"] <= classes["space"], True,
       "blank 是 space 的真子集（交付数据自洽）")
    # (c) Python 独立实现（与 glibc 无关的第二实现）
    ascii_up = [(a, b) for a, b in maps["toupper"].items() if a < 0x80]
    ascii_lo = [(a, b) for a, b in maps["tolower"].items() if a < 0x80]
    eq(len(ascii_up), 26, "toupper 覆盖 26 个 ASCII 小写字母")
    eq(len(ascii_lo), 26, "tolower 覆盖 26 个 ASCII 大写字母")
    eq(all(chr(a).upper() == chr(b) for a, b in ascii_up), True,
       "ASCII toupper 与 Python unicodedata 逐项一致")
    eq(all(chr(a).lower() == chr(b) for a, b in ascii_lo), True,
       "ASCII tolower 与 Python unicodedata 逐项一致")
    latin_up = [(a, b) for a, b in maps["toupper"].items() if a < 0x100]
    latin_lo = [(a, b) for a, b in maps["tolower"].items() if a < 0x100]
    eq(all(chr(a).upper() == chr(b) for a, b in latin_up), True,
       "Latin-1 段 toupper 与 Python unicodedata 逐项一致（%d 对）" % len(latin_up))
    eq(all(chr(a).lower() == chr(b) for a, b in latin_lo), True,
       "Latin-1 段 tolower 与 Python unicodedata 逐项一致（%d 对）" % len(latin_lo))
    # 有意的非互逆对（Unicode 事实，不是缺陷）：µ→Μ 而 tolower(Μ)=μ
    eq(maps["tolower"].get(maps["toupper"][0x00B5]), 0x03BC,
       "µ→Μ 非互逆：tolower(Μ) == μ（交付数据如实保留该 Unicode 事实）")
    check(chr(0x00B5).upper() == chr(0x039C) and chr(0x039C).lower() == chr(0x03BC),
          "Python 独立实现给出同一非互逆结论")
    eq(sum(1 for a, b in maps["toupper"].items() if maps["tolower"].get(b) != a),
       GOLDEN_NON_RECIPROCAL, "非互逆 toupper 对数 == %d（已核对的固定事实）"
       % GOLDEN_NON_RECIPROCAL)
    # 如实记录 Unicode 版本落差：定义源是 Unicode 3.2（2005 年 glibc 数据）
    drift = sorted(cp for cp in maps["toupper"]
                   if cp >= 0x100 and chr(cp).upper() != chr(maps["toupper"][cp]))
    eq(len(drift), GOLDEN_UNICODE_DRIFT,
       "如实记录版本落差：%d 个非 ASCII 大小写对与新版 unicodedata 不同" % len(drift))
    check(0x1F600 not in classes["print"],
          "unicode 3.2 之后的码位（如 U+1F600）完全不在任何类别中（消费方需回退）")

    passed = sum(1 for ok, _ in _RESULTS if ok)
    total = len(_RESULTS)
    print("\n%d 项检查，%d 项失败" % (total, total - passed))
    if passed != total:
        for ok, label in _RESULTS:
            if not ok:
                print("  - FAIL: %s" % label)
        return 1
    print("消费者用例全部通过。")
    return 0


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        sys.exit(2)
    if len(sys.argv) == 3:
        if sys.argv[2] != "--report":
            print(__doc__)
            sys.exit(2)
        sys.exit(report(sys.argv[1]))
    sys.exit(main(sys.argv))
