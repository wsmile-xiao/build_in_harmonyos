#!/usr/bin/env python3
"""Kamailio db_unixodbc 模块（db_unixodbc.so）Conan 配方 — HarmonyOS PC / aarch64。

打包口径（参照 archives/k/kamailio-snmpstats/6.0.6 同族先例）：
  - 取官方 kamailio 6.0.6 源码包全量构建，仅编译打包 db_unixodbc 模块
  - 不依赖 kamailio 本体包（模块 .so 由 kamailio 运行时 loadmodule 加载）

构建体系：kamailio 6.0.6 自带经典 Makefile 体系（src/Makefile + Makefile.defs）
  make cfg include_modules=db_unixodbc          → 生成 src/config.mak（探测 aarch64-unknown-linux-ohos）
  make modules modules=modules/db_unixodbc      → 产出 src/modules/db_unixodbc/db_unixodbc.so

模块 Makefile 的 unixODBC 探测：
  CROSS_COMPILE 为空时执行 ODBCCFG=$(shell which odbc_config)，命中则用 odbc_config --cflags/--libs；
  未命中则回退 LOCALBASE 推导（-I$(LOCALBASE)/include -L$(LOCALBASE)/lib -lodbc）。
  conan 的 unixodbc 包不含 bin/odbc_config，但构建机若存在系统 odbc_config 会被 which 命中并注入
  宿主路径，故显式传 `ODBCCFG=`（make 命令行变量优先级高于 Makefile 内部赋值）钉死回退分支，
  并以 LOCALBASE 指向 unixodbc 包目录。
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class KamailioUnixodbcConan(ConanFile):
    name = "kamailio-unixodbc"
    version = "6.0.6"
    description = ("Kamailio db_unixodbc module: SQL database connector using the "
                   "unixODBC driver manager")
    license = "GPL-2.0-or-later"
    homepage = "https://www.kamailio.org"
    url = "https://github.com/kamailio/kamailio"

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"{self.ref} supports Linux/OHOS only")

    def requirements(self):
        self.requires("unixodbc/2.3.12")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        unixodbc = self.dependencies["unixodbc"].package_folder
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"

        # R33：编译器与头/库搜索路径全部显式注入，不使用未定义的 shell 变量
        env = Environment()
        env.define("CC", cc)
        env.define("CPATH", f"{unixodbc}/include")
        env.define("LIBRARY_PATH", f"{unixodbc}/lib")

        make_vars = f"LOCALBASE={unixodbc} ODBCCFG="
        with env.vars(self).apply():
            self.run(f"make cfg include_modules=db_unixodbc {make_vars}", cwd=self.source_folder)
            self.run(f"make modules modules=modules/db_unixodbc -j1 {make_vars}",
                     cwd=self.source_folder)

        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """层 1 上游官方测试真实执行（docs/TEST_QUALITY_SPEC.md §3 / R51 三步法）。

        清点结论（完整台账见 notes.md 第四节）：官方源码包内 `test/`、`tests/` 目录共
        17 个文件（4 个目录），其中唯一自包含、无需运行中 kamailio 实例的上游测试是
        `utils/kamctl/dbtextdb/dbtextdb_test.py`（上游自带 unittest 入口，3 个用例，
        仅依赖 Python 标准库；用例数据取自同目录 `tests/` 下 10 个文件）。其余 14 个
        文件分属 janssonrpcc / rtpproxy / tm 模块或为纯数据，逐项不可执行原因见 notes.md。
        """
        test_dir = os.path.join(self.source_folder, "utils", "kamctl", "dbtextdb")
        self.output.info("upstream_test_command: python3 dbtextdb_test.py -v "
                         "(kamailio-6.0.6/utils/kamctl/dbtextdb, 3 unittest cases)")
        self.run(f'"{sys.executable}" dbtextdb_test.py -v', cwd=test_dir)

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        module_dir = os.path.join(self.source_folder, "src", "modules", "db_unixodbc")
        copy(self, "db_unixodbc.so", src=module_dir,
             dst=os.path.join(self.package_folder, "lib", "kamailio", "modules"))

    def package_info(self):
        # 模块由 kamailio 运行时 loadmodule 加载，不作为链接库供消费者使用
        self.cpp_info.libdirs = ["lib/kamailio/modules"]
        self.cpp_info.libs = []
        self.cpp_info.set_property("kamailio_modules_dir", "lib/kamailio/modules")
