#!/usr/bin/env python3
"""Kamailio lrkproxy 模块（lrkproxy.so）Conan 配方 — HarmonyOS PC / aarch64。

打包口径（参照 archives/k/kamailio-unixodbc、kamailio-snmpstats 同族先例）：
  - 取官方 kamailio 6.0.6 源码包全量构建，仅编译打包 lrkproxy 模块
  - 不依赖 kamailio 本体包（模块 .so 由 kamailio 运行时 loadmodule 加载）

构建体系：kamailio 6.0.6 自带经典 Makefile 体系（src/Makefile + Makefile.defs）
  make cfg include_modules=lrkproxy          → 生成 src/config.mak（探测 aarch64-unknown-linux-ohos）
  make modules modules=modules/lrkproxy      → 产出 src/modules/lrkproxy/lrkproxy.so

模块依赖：lrkproxy 是零外部依赖模块（Makefile 仅 `LIBS=` 空声明，链接
kamailio core 的 serlib 内部符号），无 pkg-config/xxx-config 探测分支，
无需注入 LOCALBASE —— 交叉编译只需 CC 与 OHOS sysroot。
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


# OS=harmonyos 不在 Makefile.defs 的平台分支内，此处提供 linux 分支等价探测宏。
# 每个宏的符号均已对照 OHOS SDK（musl 语义）sysroot 头文件实证存在（与
# kamailio-uuid/6.0.6 同源码包同方案）：gethostbyname2 (netdb.h, _GNU_SOURCE
# 守卫内)、sched_yield/sched_setscheduler (sched.h)、MSG_NOSIGNAL/msg_control
# (sys/socket.h)、timegm (time.h)、ip_mreqn (netinet/in.h)、alloca.h。
# HAVE_UNION_SEMUN 不注入：musl sys/sem.h 不导出 union semun。
PLATFORM_DEFS = (
    "-D_GNU_SOURCE",
    "-DHAVE_GETHOSTBYNAME2",
    "-DHAVE_SCHED_YIELD",
    "-DHAVE_MSG_NOSIGNAL",
    "-DHAVE_MSGHDR_MSG_CONTROL",
    "-DHAVE_ALLOCA_H",
    "-DHAVE_TIMEGM",
    "-DHAVE_SCHED_SETSCHEDULER",
    "-DHAVE_IP_MREQN",
)


class KamailioLrkproxyConan(ConanFile):
    name = "kamailio-lrkproxy"
    version = "6.0.6"
    description = ("Kamailio lrkproxy module: LRK-based media relay proxy "
                   "control (user agent for the LRK media proxy)")
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
        # 零外部依赖：模块 Makefile 仅链接 kamailio core 内部符号（serlib）
        pass

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"

        # R33：编译器显式注入，不使用未定义的 shell 变量。
        # lrkproxy 无外部依赖，无需 LOCALBASE/CPATH/LIBRARY_PATH 注入。
        # extra_defs：OS=harmonyos 不在 Makefile.defs 平台分支内，注入 linux
        # 分支等价探测宏（kamailio-uuid/6.0.6 同源码包已验证方案，0 补丁）。
        env = Environment()
        env.define("CC", cc)

        make_vars = f"extra_defs='{' '.join(PLATFORM_DEFS)}'"
        with env.vars(self).apply():
            self.run(f"make cfg include_modules=lrkproxy {make_vars}",
                     cwd=self.source_folder)
            self.run(f"make modules modules=modules/lrkproxy -j1 {make_vars}",
                     cwd=self.source_folder)

        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """层 1 上游官方测试真实执行（docs/TEST_QUALITY_SPEC.md §3 / R51 三步法）。

        清点结论（完整台账见 test_package/MANIFEST.yml）：官方源码包内 `test/`、
        `tests/` 目录共 17 个文件（4 个目录），其中唯一自包含、无需运行中 kamailio
        实例的上游测试是 `utils/kamctl/dbtextdb/dbtextdb_test.py`（上游自带
        unittest 入口，3 个用例，仅依赖 Python 标准库）。其余 14 个文件分属
        janssonrpcc / rtpproxy / tm 模块或为纯数据，逐项不可执行原因见 MANIFEST.yml。
        """
        test_dir = os.path.join(self.source_folder, "utils", "kamctl", "dbtextdb")
        self.output.info("upstream_test_command: python3 dbtextdb_test.py -v "
                         "(kamailio-6.0.6/utils/kamctl/dbtextdb, 3 unittest cases)")
        self.run(f'"{sys.executable}" dbtextdb_test.py -v', cwd=test_dir)

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        module_dir = os.path.join(self.source_folder, "src", "modules", "lrkproxy")
        copy(self, "lrkproxy.so", src=module_dir,
             dst=os.path.join(self.package_folder, "lib", "kamailio", "modules"))

    def package_info(self):
        # 模块由 kamailio 运行时 loadmodule 加载，不作为链接库供消费者使用
        self.cpp_info.libdirs = ["lib/kamailio/modules"]
        self.cpp_info.libs = []
        self.cpp_info.set_property("kamailio_modules_dir", "lib/kamailio/modules")
