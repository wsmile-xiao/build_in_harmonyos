#!/usr/bin/env python3
"""Kamailio debugger 模块（debugger.so）Conan 配方 — HarmonyOS PC / aarch64。

打包口径（参照 archives/k/kamailio-snmpstats/6.0.6、kamailio-unixodbc/6.0.6 与
kamailio-outbound/6.0.6 同族先例）：
  - 取官方 kamailio 6.0.6 源码包全量构建，仅编译打包 debugger 模块
  - 不依赖 kamailio 本体包（模块 .so 由 kamailio 运行时 loadmodule "debugger.so" 加载）

构建体系：kamailio 6.0.6 自带经典 Makefile 体系（src/Makefile + Makefile.defs）
  make cfg include_modules=debugger      → 生成 src/config.mak（探测 aarch64-unknown-linux-ohos）
  make modules modules=modules/debugger  → 产出 src/modules/debugger/debugger.so

debugger 模块自身无外部库依赖（src/modules/debugger/Makefile 中 LIBS= 为空，纯 core 插件），
  故配方无第三方包依赖，也不需要 LOCALBASE/pkgs 探测钉死：该 Makefile 内不存在
  pkg-config / odbc_config / net-snmp-config 分支，无宿主路径污染面。
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class KamailioDebuggerConan(ConanFile):
    name = "kamailio-debugger"
    version = "6.0.6"
    description = ("Kamailio debugger module: runtime control of the configuration "
                   "script execution (breakpoints, tracing, per-module log levels)")
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

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"

        # R33：编译器显式注入，不使用未定义的 shell 变量
        env = Environment()
        env.define("CC", cc)

        with env.vars(self).apply():
            self.run("make cfg include_modules=debugger", cwd=self.source_folder)
            self.run("make modules modules=modules/debugger -j1", cwd=self.source_folder)

        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """层 1 上游官方测试真实执行（R51 三步法）。

        清点结论（完整台账见 notes.md 第四节）：官方源码包内 `test/`、`tests/` 目录共
        17 个文件（4 个目录），其中唯一自包含、无需运行中 kamailio 实例的上游测试是
        `utils/kamctl/dbtextdb/dbtextdb_test.py`（上游自带 unittest 入口，3 个用例，
        仅依赖 Python 标准库；用例数据取自同目录 `tests/` 下 10 个文件）。debugger 模块
        自身源码目录 src/modules/debugger/ 内无测试源、无 check/ctest 目标注册；其余 14 个
        文件分属 janssonrpcc / rtpproxy / tm 模块或为纯数据，逐项不可执行原因见 notes.md。
        """
        test_dir = os.path.join(self.source_folder, "utils", "kamctl", "dbtextdb")
        self.output.info("upstream_test_command: python3 dbtextdb_test.py -v "
                         "(kamailio-6.0.6/utils/kamctl/dbtextdb, 3 unittest cases)")
        self.run(f'"{sys.executable}" dbtextdb_test.py -v', cwd=test_dir)

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        module_dir = os.path.join(self.source_folder, "src", "modules", "debugger")
        copy(self, "debugger.so", src=module_dir,
             dst=os.path.join(self.package_folder, "lib", "kamailio", "modules"))

    def package_info(self):
        # 模块由 kamailio 运行时 loadmodule 加载，不作为链接库供消费者使用（R38：非 CLI 包）
        self.cpp_info.libdirs = ["lib/kamailio/modules"]
        self.cpp_info.libs = []
        self.cpp_info.set_property("kamailio_modules_dir", "lib/kamailio/modules")
