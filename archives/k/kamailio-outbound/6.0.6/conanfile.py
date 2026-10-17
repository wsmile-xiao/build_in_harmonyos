#!/usr/bin/env python3
"""Kamailio outbound 模块（outbound.so）Conan 配方 — HarmonyOS PC / aarch64。

打包口径（参照 archives/k/kamailio-snmpstats/6.0.6 与 kamailio-unixodbc/6.0.6 同族先例）：
  - 取官方 kamailio 6.0.6 源码包全量构建，仅编译打包 outbound 模块
  - 不依赖 kamailio 本体包（模块 .so 由 kamailio 运行时 loadmodule "outbound.so" 加载）

构建体系：kamailio 6.0.6 自带经典 Makefile 体系（src/Makefile + Makefile.defs）
  make cfg include_modules=outbound      → 生成 src/config.mak（探测 aarch64-unknown-linux-ohos）
  make modules modules=modules/outbound  → 产出 src/modules/outbound/outbound.so

模块 Makefile 的 OpenSSL 探测（src/modules/outbound/Makefile:8-43）：
  CROSS_COMPILE 为空时执行 BUILDER=$(shell which pkg-config)，命中则用
  pkg-config --cflags/--libs libssl|libcrypto；未命中则回退 LOCALBASE 推导
  （-I$(LOCALBASE)/ssl/include -L$(LOCALBASE)/lib -lssl -lcrypto）。
  构建机存在 pkg-config 时会被 which 命中并注入宿主 OpenSSL 路径（交叉编译污染），
  故显式传 `BUILDER=`（make 命令行变量优先级高于 Makefile 内部赋值）钉死回退分支，
  LOCALBASE 指向 conan openssl 包目录；头文件经 CPATH 指向该包的 include
  （回退分支写的 $(LOCALBASE)/ssl/include 在 conan 包布局下不存在，CPATH 提供真实路径）。

OpenSSL 静态化（R26：系统同名库禁止动态链接）：conan openssl 默认 shared=False，
  模块静态吸收 libssl/libcrypto，实测产物 DT_NEEDED 仅 libc.so，不污染目标机 /lib 同名库。
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class KamailioOutboundConan(ConanFile):
    name = "kamailio-outbound"
    version = "6.0.6"
    description = ("Kamailio outbound module: RFC 5626 (Outbound) and RFC 5627 "
                   "(GRUU) support for SIP flow and registration handling")
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
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        # 源码下载加固（PR #12957 CI 构建 #62737 实测）：CI worker 到 www.kamailio.org
        # 的链路抖动，下载读到 11.5MB/13.2MB(87%) 后 "Read timed out"，conan 默认仅重试
        # 2 次 × 5s（tools.files.download:retry / retry_wait），不足以跨过一次抖动；
        # 且该 worker 无 curl（预下载回退不可用），只能靠 conan 自身的重试。
        # 故显式调高重试次数与间隔。源码 URL/sha256 保持官方源不变（R39/PF7）。
        get(self, **self.conan_data["sources"], strip_root=True, retry=6, retry_wait=20)

    def build(self):
        apply_conandata_patches(self)

        openssl = self.dependencies["openssl"].package_folder
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"

        # R33：编译器与头/库搜索路径全部显式注入，不使用未定义的 shell 变量
        env = Environment()
        env.define("CC", cc)
        env.define("CPATH", f"{openssl}/include")
        env.define("LIBRARY_PATH", f"{openssl}/lib")

        make_vars = f"LOCALBASE={openssl} BUILDER="
        with env.vars(self).apply():
            self.run(f"make cfg include_modules=outbound {make_vars}",
                     cwd=self.source_folder)
            self.run(f"make modules modules=modules/outbound -j1 {make_vars}",
                     cwd=self.source_folder)

        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """层 1 上游官方测试真实执行（docs/TEST_QUALITY_SPEC.md §3 / R51 三步法）。

        清点结论（完整台账见 notes.md 第四节）：官方源码包内 `test/`、`tests/` 目录共
        17 个文件（4 个目录），其中唯一自包含、无需运行中 kamailio 实例的上游测试是
        `utils/kamctl/dbtextdb/dbtextdb_test.py`（上游自带 unittest 入口，3 个用例，
        仅依赖 Python 标准库；用例数据取自同目录 `tests/` 下 10 个文件）。outbound 模块自身
        源码目录 src/modules/outbound/ 内无测试源、无 check/ctest 目标注册；其余 14 个
        文件分属 janssonrpcc / rtpproxy / tm 模块或为纯数据，逐项不可执行原因见 notes.md。
        """
        test_dir = os.path.join(self.source_folder, "utils", "kamctl", "dbtextdb")
        self.output.info("upstream_test_command: python3 dbtextdb_test.py -v "
                         "(kamailio-6.0.6/utils/kamctl/dbtextdb, 3 unittest cases)")
        self.run(f'"{sys.executable}" dbtextdb_test.py -v', cwd=test_dir)

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        module_dir = os.path.join(self.source_folder, "src", "modules", "outbound")
        copy(self, "outbound.so", src=module_dir,
             dst=os.path.join(self.package_folder, "lib", "kamailio", "modules"))

    def package_info(self):
        # 模块由 kamailio 运行时 loadmodule 加载，不作为链接库供消费者使用（R38：非 CLI 包）
        self.cpp_info.libdirs = ["lib/kamailio/modules"]
        self.cpp_info.libs = []
        self.cpp_info.set_property("kamailio_modules_dir", "lib/kamailio/modules")
