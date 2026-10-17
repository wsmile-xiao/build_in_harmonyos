#!/usr/bin/env python3
"""ieee-data 数据包验证脚本。

用法: python3 test_ieee_data.py <data_dir> <package_folder>

验证的是**数据本体**而不是"文件存在"：
  * 四个 IEEE 注册表（oui / mam / oui36 / iab）的 .txt 与 .csv 必须同时存在；
  * .csv 表头与 Assignment 位宽必须符合 IEEE 规范
    （MA-L=6 hex、MA-M=7 hex、MA-S=9 hex、IAB=9 hex）；
  * .txt 中 `(hex)` 行数必须**逐注册表等于** .csv 的数据行数 —— 两种形态是
    同一份数据的两种渲染，数量不一致说明数据被截断或混入了不同版本；
  * 抽查一条真实的 MA-L 分配（Nokia Shanghai Bell 28-6F-B9 / 286FB9），
    确认 txt 与 csv 描述的是同一个厂商；
  * .lastupdate 必须是合法 Unix 时间戳；
  * 安装目录里不能混进 debian/ 打包脚本或 Makefile 等非数据文件。

任一断言失败 → 退出码 1（Conan test_package 随之失败）。
"""

import csv
import os
import sys

# 每个注册表： (名称, csv 表头, Assignment 十六进制位宽, csv 中的 Registry 值)
REGISTRIES = (
    ("oui",   "MA-L", 6),
    ("mam",   "MA-M", 7),
    ("oui36", "MA-S", 9),
    ("iab",   "IAB",  9),
)

CSV_HEADER = ["Registry", "Assignment", "Organization Name", "Organization Address"]

DATA_FILES = [f"{name}{ext}" for name, _, _ in REGISTRIES
              for ext in (".txt", ".csv")] + [".lastupdate"]

# 真实存在的 MA-L 分配，用来证明数据不是空壳
KNOWN_OUI_TXT = "28-6F-B9"
KNOWN_OUI_CSV = "286FB9"
KNOWN_VENDOR = "Nokia Shanghai Bell"

_results = []


def check(ok: bool, label: str) -> bool:
    _results.append((bool(ok), label))
    print(f"        [{'ok' if ok else 'FAIL'}] {label}")
    return bool(ok)


def count_hex_lines(path: str) -> int:
    n = 0
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if "(hex)" in line:
                n += 1
    return n


def read_csv_rows(path: str):
    with open(path, newline="", encoding="utf-8", errors="replace") as handle:
        return list(csv.reader(handle))


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: test_ieee_data.py <data_dir> <package_folder>")
        return 2

    data_dir, package_folder = sys.argv[1], sys.argv[2]

    print(f"[test] data_dir = {data_dir}")
    check(os.path.isdir(data_dir), f"share/ieee-data 目录存在 ({data_dir})")

    # ── 1. 文件齐备且非空 ────────────────────────────────────────────────
    for fn in DATA_FILES:
        path = os.path.join(data_dir, fn)
        check(os.path.isfile(path) and os.path.getsize(path) > 0,
              f"数据文件存在且非空: {fn}")

    # ── 2. 逐注册表校验 csv 表头 / 位宽 / 与 txt 的行数一致性 ─────────────
    total_records = 0
    counts = {}
    for name, registry, width in REGISTRIES:
        csv_path = os.path.join(data_dir, f"{name}.csv")
        txt_path = os.path.join(data_dir, f"{name}.txt")

        rows = read_csv_rows(csv_path)
        check(rows and rows[0] == CSV_HEADER,
              f"{name}.csv 表头符合 IEEE 规范")

        body = rows[1:]
        bad = [r for r in body if len(r) < 2 or len(r[1]) != width]
        check(not bad and body,
              f"{name}.csv 的 Assignment 位宽 == {width} hex（{len(body)} 条）")

        bad_registry = [r for r in body if r and r[0] != registry]
        check(not bad_registry,
              f"{name}.csv 的 Registry 列恒为 {registry}")

        hex_lines = count_hex_lines(txt_path)
        counts[name] = len(body)
        check(hex_lines == len(body),
              f"{name}.txt 的 (hex) 行数 == {name}.csv 数据行数 "
              f"({hex_lines} vs {len(body)})")

        total_records += len(body)

    # ── 3. 抽查真实分配：txt 与 csv 必须指向同一个厂商 ───────────────────
    with open(os.path.join(data_dir, "oui.txt"), encoding="utf-8",
              errors="replace") as handle:
        txt_text = handle.read()
    check(KNOWN_OUI_TXT in txt_text and KNOWN_VENDOR in txt_text,
          f"oui.txt 中存在真实分配 {KNOWN_OUI_TXT} → {KNOWN_VENDOR}")

    with open(os.path.join(data_dir, "oui.csv"), encoding="utf-8",
              errors="replace") as handle:
        csv_text = handle.read()
    check(KNOWN_OUI_CSV in csv_text,
          f"oui.csv 中存在同一分配的紧凑写法 {KNOWN_OUI_CSV}")

    check("(base 16)" in txt_text,
          "oui.txt 同时包含 (hex) 与 (base 16) 两种渲染形态")

    # ── 4. 数据规模：任何一次上游刷新都不会低于这个量级 ──────────────────
    check(total_records >= 50000,
          f"四个注册表合计分配数 {total_records} >= 50000")

    # ── 5. 时间戳 ───────────────────────────────────────────────────────
    stamp_path = os.path.join(data_dir, ".lastupdate")
    raw = open(stamp_path, encoding="utf-8", errors="replace").read().strip()
    check(raw.isdigit() and int(raw) > 1_000_000_000,
          f".lastupdate 是合法 Unix 时间戳 ({raw})")

    # ── 6. 安装内容纯净性：不能混进 Debian 打包脚本 / 构建文件 ────────────
    leaked = [fn for fn in os.listdir(data_dir)
              if fn in ("Makefile", "debian", "update-ieee-data")
              or fn.endswith((".sh", ".pl", ".spec"))]
    check(not leaked,
          f"安装目录只含数据文件，未混入打包/构建脚本（发现 {leaked}）")

    # ── 7. 许可证随包发布 ───────────────────────────────────────────────
    lic_dir = os.path.join(package_folder, "licenses")
    lic_files = os.listdir(lic_dir) if os.path.isdir(lic_dir) else []
    check(bool(lic_files), f"licenses/ 已随包发布（{lic_files}）")

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
