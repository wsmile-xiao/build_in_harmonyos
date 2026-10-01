#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""installation-locale 1.9 适配自检（M，非上游用例）。

用法: python3 test_layout.py <package_folder>

检查这个**纯数据包**交付形态的完整性：数据本体就位与内容指纹、上游溯源文件齐备、
许可与文档交付、安装纯净性（无隐藏文件/无构建产物/无越界目录）、以及交付清单
与 manifest.yaml 申报的数字一致。

上游 N=0：installation-locale 源包里只有 C.UTF-8.in、Makefile、TODO 与 debian/ 打包
元数据，没有测试目录、没有测试框架、没有 check/test 目标，Debian 源包也没有
debian/tests/（无 autopkgtest），故这些断言全部是**适配自检**，与消费者用例
（consumer_locale.py，89 项）分列申报。
"""

import hashlib
import os
import sys

LOCALE_REL = os.path.join("share", "i18n", "locales", "C.UTF-8.in")
DOC_REL = os.path.join("share", "doc", "installation-locale")
EXPECTED_PAYLOAD_SHA256 = "af4b0dad56d6e3426ea4da0110aa4a330d489e3ebdeb6d8f5fb393c21ca137c2"
EXPECTED_PAYLOAD_BYTES = 81642
EXPECTED_UPSTREAM = (
    "upstream/Makefile",
    "upstream/TODO",
    "upstream/debian/changelog",
    "upstream/debian/compat",
    "upstream/debian/control",
    "upstream/debian/copyright",
    "upstream/debian/install",
    "upstream/debian/rules",
    "upstream/debian/source/format",
)
# 交付清单（与 manifest.yaml 申报一致）：数据本体 1 + README 1 + LICENSE 1
# + 上游溯源 9（Makefile/TODO + debian/ 下 7 个）== 12 个文件
EXPECTED_DELIVERABLES = (
    LOCALE_REL.replace(os.sep, "/"),
    DOC_REL.replace(os.sep, "/") + "/README",
    *(DOC_REL.replace(os.sep, "/") + "/" + name for name in EXPECTED_UPSTREAM),
    "licenses/LICENSE",
)
EXPECTED_FILE_COUNT = len(EXPECTED_DELIVERABLES)
EXPECTED_TOTAL_BYTES = 88926
FORBIDDEN_SUFFIXES = (".o", ".a", ".so", ".so.1", ".la", ".lo", ".pyc",
                      ".tar.gz", ".tar.xz", ".tar.bz2", ".zip", ".deb", ".udeb")
# conan 自己在包目录里放的记账文件（不是本包交付物，也不受本配方控制）
CONAN_BOOKKEEPING = ("conaninfo.txt", "conanmanifest.txt")

_RESULTS = []


def check(ok, label):
    _RESULTS.append((bool(ok), label))
    print("        [%s] %s" % ("ok" if ok else "FAIL", label))
    return bool(ok)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    pkg = sys.argv[1]
    payload = os.path.join(pkg, LOCALE_REL)
    locale_dir = os.path.dirname(payload)
    doc_dir = os.path.join(pkg, DOC_REL)

    print("适配自检（M）: %s" % pkg)

    # [1] 数据本体与指纹
    check(os.path.isfile(payload), "%s 存在" % LOCALE_REL)
    if not os.path.isfile(payload):
        print("\n        [test] 数据本体缺失，后续检查无意义")
        return 1
    with open(payload, "rb") as handle:
        raw = handle.read()
    check(len(raw) == EXPECTED_PAYLOAD_BYTES,
          "数据本体字节数 == %d（实际 %d）" % (EXPECTED_PAYLOAD_BYTES, len(raw)))
    check(hashlib.sha256(raw).hexdigest() == EXPECTED_PAYLOAD_SHA256,
          "数据本体 sha256 与上游钉死值一致")
    check(raw.decode("utf-8").isascii(), "数据本体是纯 ASCII（可跨工具链搬运）")

    # [2] 数据目录纯净：只放一份 locale 定义源，不混入上游维护/构建文件
    entries = sorted(os.listdir(locale_dir)) if os.path.isdir(locale_dir) else []
    check(entries == ["C.UTF-8.in"],
          "share/i18n/locales/ 下只有 C.UTF-8.in（实际 %r）" % (entries,))

    # [3] 上游溯源文件齐备
    missing = [name for name in EXPECTED_UPSTREAM
               if not os.path.isfile(os.path.join(doc_dir, name))]
    check(not missing, "上游构建配方与打包元数据齐备（缺 %r）" % (missing,))
    makefile = os.path.join(doc_dir, "upstream", "Makefile")
    if os.path.isfile(makefile):
        body = open(makefile, encoding="utf-8").read()
        check('localedef -i $^ -f "UTF-8" ./$@' in body,
              "上游 Makefile 里的 localedef 配方原样保留（溯源自证）")
    else:
        check(False, "上游 Makefile 缺失")

    # [4] 许可与文档
    license_path = os.path.join(pkg, "licenses", "LICENSE")
    check(os.path.isfile(license_path) and os.path.getsize(license_path) > 0,
          "licenses/LICENSE 已交付且非空")
    if os.path.isfile(license_path):
        text = open(license_path, encoding="utf-8").read()
        check("GPL-2.0-or-later" in text and "Copyright 2001-2005 SPIT" in text,
              "LICENSE 含 SPDX 标识与上游原始版权声明")
    check(os.path.isfile(os.path.join(doc_dir, "README"))
          and os.path.getsize(os.path.join(doc_dir, "README")) > 0,
          "share/doc/installation-locale/README 已交付且非空")

    # [5] 安装纯净性
    all_files = []
    for root, _dirs, files in os.walk(pkg):
        for name in files:
            rel = os.path.relpath(os.path.join(root, name), pkg).replace(os.sep, "/")
            if rel in CONAN_BOOKKEEPING:
                continue                      # conan 的记账文件，不算本包交付物
            all_files.append(rel)
    hidden = [f for f in all_files if any(p.startswith(".") for p in f.split("/"))]
    check(not hidden, "包内无隐藏文件（JC5；发现 %r）" % (hidden[:3],))
    junk = [f for f in all_files if f.endswith(FORBIDDEN_SUFFIXES)]
    check(not junk, "包内无构建产物/归档文件（发现 %r）" % (junk[:3],))

    # [6] 交付清单（数字与 manifest.yaml 申报的 packaged 字段一致）
    check(sorted(all_files) == sorted(EXPECTED_DELIVERABLES),
          "交付文件集合与清单逐项一致（多出 %r，缺少 %r）"
          % (sorted(set(all_files) - set(EXPECTED_DELIVERABLES)),
             sorted(set(EXPECTED_DELIVERABLES) - set(all_files))))
    total = sum(os.path.getsize(os.path.join(pkg, f)) for f in all_files)
    check(len(all_files) == EXPECTED_FILE_COUNT,
          "交付文件总数 == %d（实际 %d）" % (EXPECTED_FILE_COUNT, len(all_files)))
    check(total == EXPECTED_TOTAL_BYTES,
          "交付总字节数 == %d（实际 %d）" % (EXPECTED_TOTAL_BYTES, total))
    check(all(os.path.getsize(os.path.join(pkg, f)) > 0 for f in all_files),
          "包内没有零字节的交付文件")

    passed = sum(1 for ok, _ in _RESULTS if ok)
    total_checks = len(_RESULTS)
    print("\n        [test] %d/%d assertions passed" % (passed, total_checks))
    if passed != total_checks:
        for ok, label in _RESULTS:
            if not ok:
                print("  - %s" % label)
        return 1
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
