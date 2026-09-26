#!/usr/bin/env python3
"""iso-flags-svg 数据包验证脚本。

用法: python3 test_iso_flags.py <data_dir> <package_folder>

验证的是**数据本体**而不是"文件存在"：
  * 索引（iso-3166-1.csv / iso-3166-1.json）必须自洽：代码集合完全一致
    （json 的 Results 比 csv 多一个非国家条目 EU，这是上游的固定形态）；
  * 索引里的每一个 alpha-2 代码，都必须在两套旗帜目录里各有一个同名 SVG ——
    这是"索引与资源不脱节"的关键断言（少一面旗 = 下游按代码取图必然失败）；
  * 两套旗帜目录的条目数与富余条目必须与上游一致（富余的是欧盟、联合国、
    苏格兰等非 ISO 3166-1 旗帜，不允许多也不允许少）；
  * 每个 SVG 都必须是合法 XML、根元素为 svg、根元素的 width/height 尺寸
    必须落在上游约定的集合内（4:3 套 640x480 / 3:2 套 600x400；
    方形套 512x512 / 512x600）；
  * 安装目录里不能混进 Makefile / scripts / build / examples 等非数据内容。

任一断言失败 → 退出码 1（Conan test_package 随之失败）。
"""

import collections
import csv
import json
import os
import sys
import xml.etree.ElementTree as ET

CSV_HEADER = ["Code", "Country name", "Year", "ccTLD", "ISO 3166-2", "Notes"]
EXPECTED_CODES = 248
# json 的 Results 除了 248 个 ISO 3166-1 代码外，还带一个非国家条目 EU
JSON_EXTRA_KEYS = {"EU"}
EXPECTED_JSON_KEYS = EXPECTED_CODES + len(JSON_EXTRA_KEYS)

FLAG_DIRS = ("country-4x3", "country-squared")
EXPECTED_COUNTS = {"country-4x3": 262, "country-squared": 253}
EXPECTED_EXTRA = {
    "country-4x3": {"_basque", "_catalonia", "_earth_pernefeldt", "_galicia",
                    "_generic", "_olympic", "_scotland", "_united_nations",
                    "_wales", "brl", "eo", "eu", "ss", "zz"},
    "country-squared": {"brl", "eo", "eu", "ss", "zz"},
}
# 根元素 width/height 的尺寸分布（上游固定，逐一套核对）
EXPECTED_DIMS = {
    "country-4x3": {"640x480": 260, "600x400": 2},
    "country-squared": {"512x512": 252, "512x600": 1},
}

SVG_NS = "{http://www.w3.org/2000/svg}"

_results = []


def check(ok, label) -> bool:
    _results.append((bool(ok), label))
    print(f"        [{'ok' if ok else 'FAIL'}] {label}")
    return bool(ok)


def root_dimensions(path):
    """返回根 <svg> 元素的 (width, height) 字符串对；解析失败返回 (None, None)。"""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return None, None
    return root.get("width"), root.get("height")


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: test_iso_flags.py <data_dir> <package_folder>")
        return 2

    data_dir, package_folder = sys.argv[1], sys.argv[2]
    print(f"[test] data_dir = {data_dir}")
    check(os.path.isdir(data_dir), f"share/iso-flags-svg 目录存在 ({data_dir})")

    # ── 1. 索引文件齐备 ─────────────────────────────────────────────────
    csv_path = os.path.join(data_dir, "iso-3166-1.csv")
    json_path = os.path.join(data_dir, "iso-3166-1.json")
    check(os.path.isfile(csv_path) and os.path.getsize(csv_path) > 0,
          "iso-3166-1.csv 存在且非空")
    check(os.path.isfile(json_path) and os.path.getsize(json_path) > 0,
          "iso-3166-1.json 存在且非空")

    # ── 2. CSV 索引规范 ────────────────────────────────────────────────
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as handle:
        rows = list(csv.reader(handle))
    check(rows and rows[0] == CSV_HEADER,
          "iso-3166-1.csv 表头为 ISO 3166-1 六列")
    body = rows[1:]
    check(len(body) == EXPECTED_CODES,
          f"iso-3166-1.csv 数据行数 == {EXPECTED_CODES}（实际 {len(body)}）")
    codes = [r[0] for r in body]
    check(all(len(c) == 2 and c.isupper() and c.isalpha() for c in codes),
          "所有 Code 均为两位大写字母（ISO 3166-1 alpha-2）")
    check(len(set(codes)) == len(codes), "Code 无重复")
    check(all(len(r) == len(CSV_HEADER) for r in body),
          "每行均为 6 列（无被逗号截断的行）")

    # ── 3. JSON 索引与 CSV 索引必须描述同一份数据 ───────────────────────
    with open(json_path, encoding="utf-8", errors="replace") as handle:
        raw_json = json.load(handle)
    check(isinstance(raw_json, dict) and "Results" in raw_json,
          "iso-3166-1.json 顶层含 Results 段")
    index = raw_json.get("Results", {}) if isinstance(raw_json, dict) else {}
    check(isinstance(index, dict), "Results 是对象（以 alpha-2 为键）")
    check(isinstance(index, dict) and len(index) == EXPECTED_JSON_KEYS,
          f"Results 键数 == {EXPECTED_JSON_KEYS}"
          f"（实际 {len(index) if isinstance(index, dict) else 'n/a'}）")
    check(isinstance(index, dict)
          and set(index) - set(codes) == JSON_EXTRA_KEYS
          and set(codes) - set(index) == set(),
          f"Results 键集合 == csv 代码集合 + {sorted(JSON_EXTRA_KEYS)}")
    check(isinstance(index, dict) and index.get("CN", {}).get("Name") == "China",
          "Results 中 CN 的 Name 为 China（抽查真实条目）")

    # ── 4. 两套旗帜目录 ────────────────────────────────────────────────
    for name in FLAG_DIRS:
        directory = os.path.join(data_dir, name)
        if not check(os.path.isdir(directory), f"{name}/ 目录存在"):
            continue

        entries = sorted(os.listdir(directory))
        check(not [e for e in entries if not e.endswith(".svg")],
              f"{name}/ 中只含 .svg 文件")
        check(len(entries) == EXPECTED_COUNTS[name],
              f"{name}/ SVG 数量 == {EXPECTED_COUNTS[name]}（实际 {len(entries)}）")

        stems = {os.path.splitext(e)[0] for e in entries}
        missing = sorted(c for c in codes if c.lower() not in stems)
        check(not missing,
              f"{name}/ 覆盖全部 {EXPECTED_CODES} 个索引代码（缺失 {missing[:5]}）")
        extra = stems - {c.lower() for c in codes}
        check(extra == EXPECTED_EXTRA[name],
              f"{name}/ 的非国家富余条目与上游一致"
              f"（多 {sorted(extra - EXPECTED_EXTRA[name])[:5]} / "
              f"少 {sorted(EXPECTED_EXTRA[name] - extra)[:5]}）")

        # 逐个 SVG：非空、合法 XML、根元素为 svg、尺寸落在约定的集合内
        empty, bad_xml, bad_root = [], [], []
        sizes = collections.Counter()
        for entry in entries:
            path = os.path.join(directory, entry)
            if os.path.getsize(path) < 128:
                empty.append(entry)
                continue
            try:
                root = ET.parse(path).getroot()
            except ET.ParseError:
                bad_xml.append(entry)
                continue
            if root.tag != SVG_NS + "svg":
                bad_root.append(entry)
                continue
            sizes[f"{root.get('width')}x{root.get('height')}"] += 1

        check(not empty, f"{name}/ 无过小的空壳 SVG（{empty[:5]}）")
        check(not bad_xml, f"{name}/ 全部 {len(entries)} 个 SVG 均为合法 XML"
                           f"（解析失败 {bad_xml[:5]}）")
        check(not bad_root, f"{name}/ 根元素均为 svg（异常 {bad_root[:5]}）")
        observed = dict(sizes)
        check(observed == EXPECTED_DIMS[name],
              f"{name}/ 根元素尺寸分布与上游一致"
              f"（期望 {EXPECTED_DIMS[name]}，实际 {observed}）")

    # ── 5. 真实条目抽查 ────────────────────────────────────────────────
    cn_name = os.path.join(data_dir, "country-4x3", "cn.svg")
    if check(os.path.isfile(cn_name), "country-4x3/cn.svg 存在"):
        width, height = root_dimensions(cn_name)
        check(width == "640" and height == "480",
              f"country-4x3/cn.svg 根元素尺寸为 640x480（实际 {width}x{height}）")
        with open(cn_name, encoding="utf-8", errors="replace") as handle:
            check("viewBox" in handle.read(2048),
                  "country-4x3/cn.svg 带 viewBox（可无损缩放）")

    # ── 6. 安装纯净性 ──────────────────────────────────────────────────
    allowed = {"iso-3166-1.csv", "iso-3166-1.json"} | set(FLAG_DIRS)
    leaked = sorted(e for e in os.listdir(data_dir) if e not in allowed)
    check(not leaked,
          f"安装目录只含索引与两套旗帜，未混入构建/示例内容（发现 {leaked}）")

    lic_dir = os.path.join(package_folder, "licenses")
    lic_files = sorted(os.listdir(lic_dir)) if os.path.isdir(lic_dir) else []
    check(lic_files == ["COPYRIGHT.txt"],
          f"licenses/ 随包发布 COPYRIGHT.txt（实际 {lic_files}）")

    passed = sum(1 for ok, _ in _results if ok)
    total = len(_results)
    print(f"\n        [test] {passed}/{total} assertions passed")
    if passed != total:
        print("FAILED assertions:")
        for ok, label in _results:
            if not ok:
                print(f"  - {label}")
        return 1
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
