#!/usr/bin/env python3
"""Validate the installed zsdx quest data package (real structural checks).

Runs on the target: opens the packaged data.solarus, does a full CRC pass
over every member, and asserts the entry count/typology, the Solarus
root-entry contract, and quest metadata against the upstream v1.12.3 tree.
Prints real statistics (no echo-stub claims of gameplay).
"""

import sys
import zipfile
from pathlib import Path

# 上游 v1.12.3 data/ 树实测常量（zip 只含文件条目，无目录条目）
EXPECTED_ENTRIES = 1143
EXPECTED_LUA = 293
EXPECTED_DAT = 384
EXPECTED_PNG = 331
EXPECTED_OGG = 97
EXPECTED_UNCOMPRESSED = 41677322
MIN_ZIP_BYTES = 15 * 1024 * 1024   # 实测 ~20.2 MB；防截断/静默丢文件
MAX_ZIP_BYTES = 64 * 1024 * 1024
ROOT_REQUIRED = ("main.lua", "quest.dat", "project_db.dat")


def check(cond, message):
    if not cond:
        raise AssertionError(message)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_zsdx.py <package-folder>")
    pkg = Path(sys.argv[1])
    solarus_pkg = pkg / "share" / "solarus" / "zsdx" / "data.solarus"
    check(solarus_pkg.is_file(), f"data.solarus missing: {solarus_pkg}")
    size = solarus_pkg.stat().st_size
    check(MIN_ZIP_BYTES <= size <= MAX_ZIP_BYTES,
          f"data.solarus size out of range: {size}")

    license_txt = pkg / "licenses" / "license.txt"
    check(license_txt.is_file(), "licenses/license.txt missing")
    lic = license_txt.read_text(encoding="utf-8", errors="replace")
    check("GNU General Public License" in lic and "Creative Commons" in lic,
          "license.txt does not mention GNU GPL / Creative Commons")

    check(zipfile.is_zipfile(solarus_pkg), "data.solarus is not a zip archive")
    with zipfile.ZipFile(solarus_pkg) as zf:
        names = zf.namelist()
        check(len(names) == EXPECTED_ENTRIES,
              f"expected {EXPECTED_ENTRIES} entries, got {len(names)}")
        # 全量 CRC 完整性校验（逐成员解压校验；返回第一个坏成员或 None）
        check(zf.testzip() is None, "zip CRC check failed")
        # Solarus 契约：条目必须相对 data/ 为根（无顶层目录前缀）
        bad_prefix = [n for n in names
                      if n.startswith("data/") or n.startswith("zsdx-")]
        check(not bad_prefix,
              f"entries carry a directory prefix: {bad_prefix[:3]}")
        for required in ROOT_REQUIRED:
            check(required in names, f"root entry missing: {required}")
        lua = sum(1 for n in names if n.endswith(".lua"))
        dat = sum(1 for n in names if n.endswith(".dat"))
        png = sum(1 for n in names if n.endswith(".png"))
        ogg = sum(1 for n in names if n.endswith(".ogg"))
        check(lua == EXPECTED_LUA, f"expected {EXPECTED_LUA} .lua, got {lua}")
        check(dat == EXPECTED_DAT, f"expected {EXPECTED_DAT} .dat, got {dat}")
        check(png == EXPECTED_PNG, f"expected {EXPECTED_PNG} .png, got {png}")
        check(ogg == EXPECTED_OGG, f"expected {EXPECTED_OGG} .ogg, got {ogg}")
        quest_dat = zf.read("quest.dat").decode("utf-8")
        check('quest_version = "1.12.3"' in quest_dat,
              "quest.dat quest_version mismatch")
        check('solarus_version = "1.6"' in quest_dat,
              "quest.dat solarus_version mismatch")
        total = sum(i.file_size for i in zf.infolist())
        check(total == EXPECTED_UNCOMPRESSED,
              f"expected {EXPECTED_UNCOMPRESSED} uncompressed bytes, got {total}")

    print(f"OK: zsdx quest data verified: {len(names)} entries "
          f"({lua} lua / {dat} dat / {png} png / {ogg} ogg), "
          f"{total} bytes uncompressed, zip {size} bytes, CRC clean")


if __name__ == "__main__":
    main()
