#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""swe-data 4.0-20221111 —— 适配自检（M，非上游用例；上游 N=0）

上游 swe-data 是纯数据包：源包里只有 `*.se1` 星历文件、6 个文本表和一个指向
Debian 打包目录的 Makefile/README.txt 符号链接，没有测试目录、没有测试框架、
没有 `check`/`test` 目标，Debian 源包也只有 dh + install（没有 autopkgtest）。

这里的每一条都是**适配自检**：验证 conan 包交付的内容完整、可用、且与 Debian
安装布局一致。真正的端到端功能验证在 consumer_ephe.py（完整消费者用例）。
"""
from __future__ import print_function

import os
import struct
import sys

EPHE_SUBDIR = os.path.join("share", "libswe", "ephe")
EXPECTED_ROOT_SE1 = 150
EXPECTED_SAT_SE1 = 32
EXPECTED_TXT = ["seasnam.txt", "seasnam2.txt", "sedeltat.txt.inactive",
                "sefstars.txt", "seleapsec.txt", "seorbel.txt"]
EXPECTED_TOTAL_BYTES = 314404679
DE_NUMBER = 431
ENDIAN_MARKER = 97 * 65536 + 98 * 256 + 99

FAILURES = []
COUNT = [0]


def check(ok, label, detail=""):
    COUNT[0] += 1
    if not ok:
        FAILURES.append(label)
    print("  [%s] %s%s" % ("ok" if ok else "FAIL", label, ("  " + detail) if detail else ""))
    return ok


def read_header(path):
    """只读头部（3 或 4 行文本 + 定长域），返回文件名/DE 编号/时间窗/行星表。"""
    with open(path, "rb") as handle:
        data = handle.read(4096)
    for nlines in (3, 4):
        pos = 0
        lines = []
        for _ in range(nlines):
            end = data.find(b"\r\n", pos)
            if end < 0:
                break
            lines.append(data[pos:end].decode("latin-1"))
            pos = end + 2
        if len(lines) != nlines:
            continue
        if struct.unpack_from("<i", data, pos)[0] != ENDIAN_MARKER:
            continue
        nplan = struct.unpack_from("<h", data, pos + 28)[0]
        if not 1 <= nplan <= 20:
            continue
        return {
            "nlines": nlines,
            "declared_name": lines[1],
            "declared_len": struct.unpack_from("<i", data, pos + 4)[0],
            "denum": struct.unpack_from("<i", data, pos + 8)[0],
            "tfstart": struct.unpack_from("<d", data, pos + 12)[0],
            "ipl": list(struct.unpack_from("<%dh" % nplan, data, pos + 30)),
        }
    return None


def year_of(tjd):
    return 2000.0 + (tjd - 2451545.0) / 365.25


def main(argv):
    pkg = argv[1]
    ephe = os.path.join(pkg, EPHE_SUBDIR)
    sat = os.path.join(ephe, "sat")
    print("适配自检（M）: %s" % ephe)

    print("\n[1] 安装布局（与 Debian usr/share/libswe/ephe 同形）")
    check(os.path.isdir(ephe), "share/libswe/ephe 目录存在")
    check(os.path.isdir(sat), "share/libswe/ephe/sat 目录存在")

    print("\n[2] 文件清点")
    if not os.path.isdir(ephe):
        print("目录不存在，后续检查跳过")
        return 1
    roots = sorted(n for n in os.listdir(ephe)
                   if os.path.isfile(os.path.join(ephe, n)))
    root_se1 = [n for n in roots if n.endswith(".se1")]
    txt = [n for n in roots if n.endswith(".txt") or n.endswith(".inactive")]
    sat_se1 = sorted(n for n in os.listdir(sat)
                     if os.path.isfile(os.path.join(sat, n)) and n.endswith(".se1"))
    check(len(root_se1) == EXPECTED_ROOT_SE1, "ephe/ 下 *.se1 == %d" % EXPECTED_ROOT_SE1,
          "实测 %d" % len(root_se1))
    check(len(sat_se1) == EXPECTED_SAT_SE1, "ephe/sat/ 下 sepm*.se1 == %d" % EXPECTED_SAT_SE1,
          "实测 %d" % len(sat_se1))
    check(sorted(txt) == sorted(EXPECTED_TXT), "6 个文本表齐全", ",".join(txt))
    check(len(root_se1) + len(sat_se1) == 182, "全部 *.se1 == 182")

    print("\n[3] 载荷完整性（长度/字节数/DE 编号）")
    total = 0
    truncated = []
    wrong_de = []
    for name in root_se1 + sat_se1:
        path = os.path.join(ephe, name) if name in root_se1 else os.path.join(sat, name)
        size = os.path.getsize(path)
        total += size
        head = read_header(path)
        if head is None:
            truncated.append(name)
            continue
        if head["declared_len"] != size:
            truncated.append(name)
        if head["denum"] != DE_NUMBER:
            wrong_de.append("%s(DE%d)" % (name, head["denum"]))
    for name in txt:
        total += os.path.getsize(os.path.join(ephe, name))
    check(not truncated, "182 个 *.se1 头部声明长度 == 文件实际长度（无截断）",
          "" if not truncated else str(truncated[:5]))
    check(not wrong_de, "全部星历文件基于 JPL DE%d" % DE_NUMBER,
          "" if not wrong_de else str(wrong_de[:5]))
    check(total == EXPECTED_TOTAL_BYTES, "载荷总字节数 == %d" % EXPECTED_TOTAL_BYTES,
          "实测 %d" % total)

    print("\n[4] 文件名与内容自洽（libswe 的世纪索引约定）")
    bad = []
    for name in root_se1:
        head = read_header(os.path.join(ephe, name))
        if head["declared_name"].strip().lower() != name.lower():
            bad.append(name + "(文件名)")
            continue
        # sepl_/semo_/seas_ 是公元后系，seplm/semom/seasm 是公元前系（m = minus）
        negative = name[4] == "m"
        century = name[5:name.index(".")]
        if not century.isdigit():
            bad.append(name + "(索引)")
            continue
        index = int(century) * 100
        got = year_of(head["tfstart"])
        expected = -index if negative else index
        # 上游 132 一组（seplm132/semom132/seasm132）的头部窗口相对文件名整体偏移
        # ~201 年（实测 -13200 -> -12999），其余文件都在 1 年内，故按 300 年判定并
        # 在上限内视为"名实相符"。
        if abs(got - expected) > 300.0:
            bad.append("%s(tfstart=%.0f 年, 期望 %.0f)" % (name, got, expected))
    check(not bad, "每个 *.se1 文件名的世纪索引与头部时间窗一致",
          "" if not bad else str(bad[:5]))
    bad = [n for n in sat_se1
           if (read_header(os.path.join(sat, n)) or {}).get("ipl", [0])[0] != int(n[4:8])]
    check(not bad, "每个 sepm 文件的卫星编号与文件名一致（sepm9501 -> 9501）",
          "" if not bad else str(bad[:5]))

    print("\n[5] 许可与文档")
    lic = os.path.join(pkg, "licenses", "LICENSE")
    doc = os.path.join(pkg, "share", "doc", "swe-data")
    ok = os.path.isfile(lic)
    text = open(lic, encoding="utf-8").read() if ok else ""
    check(ok and "CC0-1.0" in text, "licenses/LICENSE 交付且标注 CC0-1.0")
    check(os.path.isfile(os.path.join(doc, "copyright"))
          and os.path.isfile(os.path.join(doc, "README")),
          "share/doc/swe-data/{copyright,README} 交付")

    print("\n[6] 安装纯净性（不夹带上游打包/构建产物）")
    allowed = set(root_se1) | set(txt)
    extra = [n for n in roots if n not in allowed]
    check(not extra, "ephe/ 下只有 *.se1 与文本表", "" if not extra else str(extra[:5]))
    check(not os.path.exists(os.path.join(ephe, "Makefile"))
          and not os.path.exists(os.path.join(ephe, "debian"))
          and not os.path.exists(os.path.join(ephe, "README.txt")),
          "上游 Makefile/README.txt 符号链接与 debian/ 未进入包")
    check(not os.path.exists(os.path.join(pkg, "share", "doc", "swe-data", "debian")),
          "无多余打包目录")

    print("\n" + "=" * 64)
    print("适配自检 %d 条，通过 %d 条，失败 %d 条"
          % (COUNT[0], COUNT[0] - len(FAILURES), len(FAILURES)))
    if FAILURES:
        for item in FAILURES:
            print("  - %s" % item)
        return 1
    print("[test] %d/%d assertions passed" % (COUNT[0], COUNT[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
