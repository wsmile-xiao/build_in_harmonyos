#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""libsoci 4.0.3 适配自检（M，非上游用例）。

上游官方测试是 catch + CTest 的 65 个用例（1715 条断言，见
test_package/MANIFEST.yml），在 recipe 的 build() 里跑；这里检查的是
**conan 包的交付形态**：库文件/头文件/许可/cmake 集成是否齐全、是否夹带测试程序。
"""
from __future__ import print_function

import os
import sys

FAILURES = []
COUNT = [0]


def check(ok, label, detail=""):
    COUNT[0] += 1
    if not ok:
        FAILURES.append(label)
    print("  [%s] %s%s" % ("ok" if ok else "FAIL", label, ("  " + detail) if detail else ""))
    return ok


def main(argv):
    pkg = argv[1]
    libdir = os.path.join(pkg, "lib")
    incdir = os.path.join(pkg, "include", "soci")
    libs = os.listdir(libdir) if os.path.isdir(libdir) else []
    print("适配自检（M）: %s" % pkg)

    print("\n[1] 三个库交付齐全（core + sqlite3 后端 + empty 后端）")
    for name in ("soci_core", "soci_sqlite3", "soci_empty"):
        found = [n for n in libs if n.startswith("lib" + name + ".so")
                 or n.startswith("lib" + name + ".a")]
        check(bool(found), "lib/libsoci_%s.(so|a)" % name.replace("soci_", ""), ",".join(found[:3]))

    print("\n[2] 公开头文件（消费者只需 -I include）")
    for rel in ("soci.h", "soci-backend.h", "session.h", "rowset.h", "soci-config.h",
                os.path.join("sqlite3", "soci-sqlite3.h")):
        check(os.path.isfile(os.path.join(incdir, rel)), "include/soci/%s" % rel)

    print("\n[3] CMake 集成与许可、安装纯净性")
    cmake_cfg = os.path.join(pkg, "lib", "cmake", "SOCI", "SOCIConfig.cmake")
    check(os.path.isfile(cmake_cfg), "lib/cmake/SOCI/SOCIConfig.cmake 交付")
    check(os.path.isfile(os.path.join(pkg, "licenses", "LICENSE_1_0.txt")),
          "licenses/LICENSE_1_0.txt（BSL-1.0）")
    test_bins = [n for n in os.listdir(os.path.join(pkg, "bin"))
                 if n.endswith(("_test", "_test.exe"))] if os.path.isdir(os.path.join(pkg, "bin")) else []
    check(not test_bins, "未夹带上游测试程序", ",".join(test_bins))
    check("SOCI_HAVE_CXX11" in open(os.path.join(incdir, "soci-config.h")).read(),
          "soci-config.h 声明 SOCI_HAVE_CXX11（与消费者 C++17 一致）")

    print("\n" + "=" * 60)
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
