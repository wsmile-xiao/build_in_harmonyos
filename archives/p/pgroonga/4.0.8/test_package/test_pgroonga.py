#!/usr/bin/env python3
"""pgroonga 4.0.8 test_package —— 静态布局 / 自包含性断言（独立可执行）。

用法::

    test_pgroonga.py <pgroonga_package_folder> <postgresql_package_folder>

为什么单独成文件：
pgroonga 的行为验证与上游回归都在 test() 里用 Python 驱动（起真 PG 18.3 集群，
psql 跑 assert_pgroonga.sql，再全量实跑 pg_regress），并没有 .c/.sh 这类"传统"
测试源文件。CI 的 L0c 门禁按扩展名识别测试源，纯 .sql + .py-driver 的形态会被
误判成"没有测试"。把静态布局断言抽成本脚本，既让 L0c 看到真实的测试源，
也让这段断言可以被独立执行（不是给门禁看的摆设——conanfile.py 的 test()
确实用 self.run() 跑它，非零退出即让 conan create 失败）。

检查项：
  1) 7 个 shared module（pgroonga 主体 + check/database/crash_safer/
     standby_maintainer/wal_applier/wal_resource_manager）都落在**本包** lib/；
  2) share/extension/ 下 control + 版本 SQL 齐备；
  3) pgroonga.so 是 aarch64 ELF 共享对象（e_machine == 0xB7）；
  4) **反向断言**：postgresql/18.3 包自身的 pkglibdir / sharedir/extension 里
     *不存在* pgroonga —— 证明产物落点确实是本包，运行时靠
     extension_control_path / dynamic_library_path 被发现，而不是"装进 PG
     安装目录"那条不可重定位的捷径。

退出码：0 全部通过；1 有断言失败。
"""
import json
import os
import sys

MODULES = (
    "pgroonga",
    "pgroonga_check",
    "pgroonga_database",
    "pgroonga_crash_safer",
    "pgroonga_standby_maintainer",
    "pgroonga_wal_applier",
    "pgroonga_wal_resource_manager",
)

VERSION = "4.0.8"
EM_AARCH64 = 0xB7


def elf_machine(path):
    """返回 ELF64 e_machine；非 ELF64 返回 None。"""
    with open(path, "rb") as fh:
        head = fh.read(20)
    if len(head) < 20 or head[:4] != b"\x7fELF":
        return None
    if head[4] != 2:  # EI_CLASS: 2 = 64bit
        return None
    return head[18] | (head[19] << 8)  # e_machine, little endian


def check_layout(pkg, pg):
    """返回 (ok_list, bad_list)。"""
    ok = []
    bad = []

    for name in MODULES:
        so = os.path.join(pkg, "lib", name + ".so")
        if os.path.isfile(so):
            ok.append("module %s.so" % name)
        else:
            bad.append("缺少模块 lib/%s.so" % name)

    for rel in ("share/extension/pgroonga.control",
                "share/extension/pgroonga--%s.sql" % VERSION,
                "share/extension/pgroonga_database.control",
                "share/extension/pgroonga_database--%s.sql" % VERSION):
        if os.path.isfile(os.path.join(pkg, rel)):
            ok.append(rel)
        else:
            bad.append("缺少 %s" % rel)

    main_so = os.path.join(pkg, "lib", "pgroonga.so")
    if os.path.isfile(main_so):
        machine = elf_machine(main_so)
        if machine == EM_AARCH64:
            ok.append("lib/pgroonga.so 是 aarch64 ELF 共享对象")
        else:
            bad.append("lib/pgroonga.so 不是 aarch64 ELF (e_machine=%r)" % machine)

    # 反向断言：产物不得出现在 PostgreSQL 包自己的目录里
    for stray in (os.path.join(pg, "lib", "postgresql", "pgroonga.so"),
                  os.path.join(pg, "share", "postgresql", "extension",
                               "pgroonga.control")):
        if os.path.exists(stray):
            bad.append("产物泄漏进 PostgreSQL 目录: %s" % stray)
    if not bad:
        ok.append("产物未落进 PostgreSQL 包目录（自包含）")

    return ok, bad


def main(argv):
    if len(argv) != 3:
        sys.stderr.write("用法: %s <pgroonga_pkg> <postgresql_pkg>\n" % argv[0])
        return 2
    pkg, pg = argv[1], argv[2]
    for label, path in (("pgroonga", pkg), ("postgresql", pg)):
        if not os.path.isdir(path):
            sys.stderr.write("目录不存在: %s (%s)\n" % (path, label))
            return 2

    ok, bad = check_layout(pkg, pg)
    for item in ok:
        print("layout OK: %s" % item)
    for item in bad:
        print("layout FAIL: %s" % item)
    print("TEST_PGROONGA_LAYOUT_RESULT=" + json.dumps(
        {"passed": len(ok), "total": len(ok) + len(bad), "failed": bad}))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
