#!/usr/bin/env python3
"""Conan recipe — libdb 5.3.35 (Berkeley DB, community fork) — Meson project.

上游是 https://github.com/berkeleydb/libdb —— Berkeley DB 的社区 fork
（README 首行声明 "Not affiliated with or endorsed by Oracle"；Oracle 最后
一个 5.3 版本是 5.3.28，v5.3.29 及之后都是该 fork 的社区发布）。本条目与
仓内 `berkeley-db5/5.3.28`（源码 download.oracle.com/db-5.3.28.tar.gz）、
`db/6.2.32`（Oracle 6.x 线，AGPL）互为独立软件条目：源码来源、项目主页、
版本线、许可证表述都不同。

构建体系：本 fork 在 `master` 上新增了 Meson 构建（`meson.build` +
`dist/meson.build`，dist/configure.ac 的 autotools 路径保留为历史参考）。
本配方走 Meson —— 它对 OHOS 的价值是**整条绕开 autoconf 生成物**：

  BDB 的 autotools 路径（5.3.28 / 6.2.32 两条已入库配方均实证）在 HMDFS
  上必须处理三类环境坑：① dist/configure 的 `print -r --` 回显探测假阳性
  （ksh 内建 → config.status 运行时报 `print: command not found`）；
  ② config.status 的 `(umask 077 && mktemp -d ./confXXXXXX)` 在 setgid
  HMDFS 目录上拒写；③ config.guess/config.sub（2011-11-11 版）不认
  HarmonyOS 三元组。Meson 不生成 config.status / libtool，这三类问题
  一次都不出现——只有 Meson 自己的 `mesonbuild` 在跑。

产物范围：Meson 构建只产出核心 C 库（B-tree/Hash/Heap/Queue/Recno、lock、
log、mpool、txn、replication、crypto、compression），不含 C++/Java/Tcl/SQL
绑定与 db_* 命令行工具（那是 dist/configure.ac 的管线）。因此
package_type=library，无 bin/、无 commands.json（L0k 对齐）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain


class LibdbConan(ConanFile):
    name = "libdb"
    version = "5.3.35"
    description = (
        "Berkeley DB (community fork, berkeleydb/libdb) — embedded transactional "
        "key/value storage engine (B-tree/Hash/Heap/Queue/Recno) with ACID "
        "transactions, locking, write-ahead logging, MVCC snapshot isolation and "
        "replication"
    )
    license = "AGPL-3.0-or-later OR Sleepycat"
    homepage = "https://github.com/berkeleydb/libdb"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # R26: 系统同名库默认静态（libdb 是典型的系统库名）
    default_options = {"shared": False}

    # OHOS 工具链 bin（Meson 探测 compiler/archiver 需要 PATH 里有它们）
    _HNP_BIN = "/data/service/hnp/bin"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libdb/5.3.35 unsupported os: %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        # 精确版本（L0：tool_requires 不得带版本范围）。meson/1.11.0 在 ohpcd
        # 上有 OHOS armv8 / clang 15 / Release 的制品包（2026-08-16 上架），
        # 同款先例 c-shquote / c-utf8 / c-stdaux / account-utils / cairo。
        self.tool_requires("meson/1.11.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # MesonToolchain 只用来建立 conanbuild 环境（self.run(..., env="conanbuild")
        # 依赖它注入的 CC/CXX/CFLAGS 等）。实际构建走 c-shquote/1.1.0 的先例：
        # 手动执行 meson，构建选项以 -D 形式显式给出，**不使用** conan 生成的
        # native file（先例 astroterm/1.0.9 用 native file 时需要额外往 [binaries]
        # 注入 archiver，本配方按 c-shquote 的直连方式绕开该不确定点）。
        MesonToolchain(self).generate()

    def _meson_prefix(self):
        # Meson 工具类不加载自定义 env（c-shquote / account-utils 先例），
        # build() 手动执行 meson，PATH/CC/AR 显式前置。
        return (
            "PATH=%s:$PATH " % self._HNP_BIN
            + "CC=%s " % os.path.join(self._HNP_BIN, "clang")
            + "AR=%s " % os.path.join(self._HNP_BIN, "llvm-ar")
        )

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        bdir = self.build_folder
        libtype = "shared" if self.options.shared else "static"
        setup = (
            "meson setup %s %s --buildtype=release -Ddefault_library=%s "
            "-Dhegel=disabled" % (bdir, src, libtype)
        )
        self.run(self._meson_prefix() + setup, cwd=bdir, env="conanbuild")
        # -j1 是铁律（OHOS 沙箱不支持 mkfifo，jobserver 会炸）
        self.run(
            "PATH=%s:$PATH meson compile -C %s -j1" % (self._HNP_BIN, bdir),
            env="conanbuild",
        )
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """跑上游 Meson 注册的 gating 测试层（suite `tiers`，1 项：
        test/tiers/test_iso_anomaly —— 并发事务调度下的可串行化校验，
        verdict 由模型枚举算出而非硬编码）。

        上游 test/tiers/meson.build 把三个 tier 分成三个 suite：
          tiers        B1 isolation，gating，本配方执行
          tiers-xfail  B3 lock-matrix，上游注释原文 "aborts on current master:
                       that abort IS the #140 reproduction" → 故意红，不执行
          tiers-slow   B2 soak（-n 2000，timeout 1800）→ 分钟级 soak，不执行

        测试目标 `build_by_default: false`，所以先按名编译再 --no-rebuild 跑
        （不在 meson test 里触发重建，避免沙箱下重建调用链的不确定性）。
        上游注释给出的等价命令行：
          ninja -C build test/tiers/test_iso_anomaly
          meson test -C build --suite tiers
        """
        bdir = self.build_folder
        target = "test/tiers/test_iso_anomaly"
        self.run(
            "PATH=%s:$PATH meson compile -C %s -j1 %s"
            % (self._HNP_BIN, bdir, target),
            env="conanbuild",
        )
        self.run(
            "PATH=%s:$PATH meson test -C %s --suite tiers --no-rebuild "
            "--print-errorlogs" % (self._HNP_BIN, bdir),
            env="conanbuild",
        )

    def package(self):
        # 上游 meson 只 install 库本体（dist/meson.build 的 library() 没有
        # install_headers），公开 db.h 是 gen_header.py 由 src/dbinc/db.in
        # 渲染出的 custom_target 产物，落在 <build>/dist/db.h。
        # HMDFS 上不做 meson install（先例 c-shquote/1.1.0），按产物实体拷贝。
        build_dist = os.path.join(self.build_folder, "dist")
        if not os.path.isfile(os.path.join(build_dist, "db.h")):
            raise ConanInvalidConfiguration(
                "generated public header missing: %s"
                % os.path.join(build_dist, "db.h")
            )
        copy(
            self, "db.h",
            src=build_dist,
            dst=os.path.join(self.package_folder, "include"),
        )
        libdir = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            copy(self, "libdb.so*", src=build_dist, dst=libdir)
        else:
            copy(self, "libdb.a", src=build_dist, dst=libdir)
        if not os.path.isdir(libdir) or not os.listdir(libdir):
            raise ConanInvalidConfiguration(
                "no library artifact produced under %s" % build_dist
            )

    def package_info(self):
        self.cpp_info.libs = ["db"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "libdb")
        self.cpp_info.set_property("cmake_target_name", "libdb::libdb")
        self.cpp_info.set_property("pkg_config_name", "libdb")
        if self.settings.os == "OHOS":
            # pthread：BDB 的 mutex/latch 实现直接依赖 POSIX 线程
            self.cpp_info.system_libs = ["pthread"]
