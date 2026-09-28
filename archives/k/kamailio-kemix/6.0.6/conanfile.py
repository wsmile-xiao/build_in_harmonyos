#!/usr/bin/env python3
"""Kamailio kemix 模块（kemix.so）Conan 配方 — HarmonyOS PC / aarch64。

打包口径：
  - 取官方 kamailio 6.0.6 源码包全量构建，仅编译打包 kemix 模块
  - 不依赖 kamailio 本体包（模块 .so 由 kamailio 运行时 loadmodule 加载）
  - 无外部库依赖（模块 Makefile 的 LIBS 为空，仅引用 kamailio core 符号）

构建体系：kamailio 6.0.6 自带经典 Makefile 体系（src/Makefile + Makefile.defs）
  make cfg include_modules=kemix           → 生成 src/config.mak（探测 aarch64-unknown-linux-ohos）
  make modules modules=modules/kemix       → 产出 src/modules/kemix/kemix.so

kemix 是 KEMI 扩展模块：exports 结构本身零导出（无 cfg 命令/RPC/伪变量/mod_init），
全部功能在加载期通过 mod_register() → sr_kemi_modules_add(sr_kemi_kx_exports) 注册，
函数前缀模块名 "kx"（KEMI 调用侧为 KSR.kx.*：get_ruri/get_ruser/get_body/get_callid …）。
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class KamailioKemixConan(ConanFile):
    name = "kamailio-kemix"
    version = "6.0.6"
    description = ("Kamailio kemix module: KEMI extensions providing the KSR.kx.* "
                   "function family")
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
            self.run("make cfg include_modules=kemix", cwd=self.source_folder)
            self.run("make modules modules=modules/kemix -j1", cwd=self.source_folder)

        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """层 1 上游官方测试真实执行（docs/TEST_QUALITY_SPEC.md §3 / R51 三步法）。

        清点结论（完整台账见 notes.md 第四节）：官方源码包内 `test/`、`tests/` 目录共
        17 个文件（4 个目录），其中唯一自包含、无需运行中 kamailio 实例的上游测试是
        `utils/kamctl/dbtextdb/dbtextdb_test.py`（上游自带 unittest 入口，3 个用例，
        仅依赖 Python 标准库；用例数据取自同目录 `tests/` 下 10 个文件）。其余 14 个
        文件分属 janssonrpcc / rtpproxy / tm 模块或为纯数据，逐项不可执行原因见 notes.md。
        kemix 模块自身在源码包内无任何测试文件（src/modules/kemix/ 仅含 C 源与 doc/）。
        """
        test_dir = os.path.join(self.source_folder, "utils", "kamctl", "dbtextdb")
        self.output.info("upstream_test_command: python3 dbtextdb_test.py -v "
                         "(kamailio-6.0.6/utils/kamctl/dbtextdb, 3 unittest cases)")
        self.run(f'"{sys.executable}" dbtextdb_test.py -v', cwd=test_dir)

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        module_dir = os.path.join(self.source_folder, "src", "modules", "kemix")
        copy(self, "kemix.so", src=module_dir,
             dst=os.path.join(self.package_folder, "lib", "kamailio", "modules"))

    def package_info(self):
        # 模块由 kamailio 运行时 loadmodule 加载，不作为链接库供消费者使用
        self.cpp_info.libdirs = ["lib/kamailio/modules"]
        self.cpp_info.libs = []
        self.cpp_info.set_property("kamailio_modules_dir", "lib/kamailio/modules")
