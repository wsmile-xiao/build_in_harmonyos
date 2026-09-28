#!/usr/bin/env python3
"""Kamailio snmpstats 模块（snmpstats.so）Conan 配方 — HarmonyOS PC / aarch64。

打包口径（参照 archives/a/asterisk-srtp/22.10.1 先例）：
  - 取官方 kamailio 6.0.6 源码包全量构建，仅编译打包 snmpstats 模块
  - 不依赖 kamailio 本体包（模块 .so 由 kamailio 运行时 loadmodule 加载）

构建体系：kamailio 6.0.6 自带经典 Makefile 体系（src/Makefile + Makefile.defs）
  make cfg include_modules=snmpstats            → 生成 src/config.mak（探测 aarch64-unknown-linux-ohos）
  make modules modules=modules/snmpstats        → 产出 src/modules/snmpstats/snmpstats.so

snmpstats 走 AgentX 子代理路径，链接 net-snmp 的 agent 系库；模块 Makefile 在找不到
net-snmp-config 时使用 LOCALBASE 推导头/库路径，故以 LOCALBASE 指向 net-snmp 包并清空
BUILDER——该包 net-snmp-config --prefix 为 "/"，会给出 `-L//lib` 这类无效路径。
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class KamailioSnmpstatsConan(ConanFile):
    name = "kamailio-snmpstats"
    version = "6.0.6"
    description = ("Kamailio snmpstats module: exports SIP server statistics through an "
                   "SNMP AgentX subagent")
    license = "GPL-2.0-or-later"
    homepage = "https://www.kamailio.org"
    url = "https://github.com/kamailio/kamailio"

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"{self.ref} supports Linux/OHOS only")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("net-snmp/5.9.4")
        # net-snmp 公开头文件包含 openssl 头，需其 include 路径
        self.requires("openssl/3.5.6")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        net_snmp = self.dependencies["net-snmp"].package_folder
        openssl = self.dependencies["openssl"].package_folder
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"

        # R33：编译器与头/库搜索路径全部显式注入，不使用未定义的 shell 变量
        env = Environment()
        env.define("CC", cc)
        env.define("CPATH", f"{net_snmp}/include:{openssl}/include")
        env.define("LIBRARY_PATH", f"{net_snmp}/lib:{openssl}/lib")

        make_vars = f"LOCALBASE={net_snmp} BUILDER="
        with env.vars(self).apply():
            self.run(f"make cfg include_modules=snmpstats {make_vars}", cwd=self.source_folder)
            self.run(f"make modules modules=modules/snmpstats -j1 {make_vars}",
                     cwd=self.source_folder)

        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """层 1 上游官方测试真实执行（R51 三步法；完整台账见 notes.md 第四节）。

        清点口径：官方源码包内 `test/`、`tests/` 目录文件共 17 个
        （utils/kamctl/dbtextdb/tests 10 + src/modules/janssonrpcc/test 3 +
        src/modules/rtpproxy/test 3 + src/modules/tm/test 1）；snmpstats 模块目录
        `src/modules/snmpstats/` 内无任何测试文件、无 check/ctest 目标注册。

        实跑项：17 个文件中唯一自包含、无需运行中 kamailio 实例的上游测试是
        `utils/kamctl/dbtextdb/dbtextdb_test.py`（上游自带 unittest 入口，3 个用例，
        仅依赖 Python 标准库；用例数据取自同目录 tests/ 下 10 个文件）。
        """
        test_dir = os.path.join(self.source_folder, "utils", "kamctl", "dbtextdb")
        self.output.info("upstream_test_command: python3 dbtextdb_test.py -v "
                         "(kamailio-6.0.6/utils/kamctl/dbtextdb, 3 unittest cases)")
        self.run(f'"{sys.executable}" dbtextdb_test.py -v', cwd=test_dir)

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        module_dir = os.path.join(self.source_folder, "src", "modules", "snmpstats")
        copy(self, "snmpstats.so", src=module_dir,
             dst=os.path.join(self.package_folder, "lib", "kamailio", "modules"))
        copy(self, "KAMAILIO*", src=os.path.join(module_dir, "mibs"),
             dst=os.path.join(self.package_folder, "share", "snmp", "mibs"))

    def package_info(self):
        # 模块由 kamailio 运行时 loadmodule 加载，不作为链接库供消费者使用
        self.cpp_info.libdirs = ["lib/kamailio/modules"]
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.libs = []
        self.cpp_info.set_property("kamailio_modules_dir", "lib/kamailio/modules")
