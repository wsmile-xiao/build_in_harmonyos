#!/usr/bin/env python3
"""Kamailio xmlops 模块（xmlops.so）Conan 配方 — HarmonyOS PC / aarch64。

打包口径（参照 archives/k/kamailio-tls/6.0.6、kamailio-snmpstats/6.0.6 同族先例）：
  - 取官方 kamailio 6.0.6 源码包全量构建，仅编译打包 xmlops 模块
    （积分赛任务 kamailio-xml 对应 kamailio 源码树内的 xmlops 模块）
  - 不依赖 kamailio 本体包（模块 .so 由 kamailio 运行时 loadmodule 加载）

构建体系：kamailio 6.0.6 自带经典 Makefile 体系（src/Makefile + Makefile.defs）
  make cfg include_modules=xmlops        → 生成 src/config.mak
  make modules modules=modules/xmlops    → 产出 src/modules/xmlops/xmlops.so

平台差异（详见同目录 notes.md）：
1) 平台探测宏：Makefile.defs 只处理 linux/solaris/freebsd/darwin 等分支，OS=harmonyos
   不注入任何 HAVE_* 探测宏，core 头直接 #error。故经 extra_defs 注入 linux 分支
   等价宏集（宏集与 kamailio-tls 同族先例一致，均对照 OHOS SDK sysroot 实证）。
2) libxml2 探测：模块 Makefile 在 CROSS_COMPILE 为空时用构建机 xml2-config /
   pkg-config 探测 libxml2；显式传 PKGCFGTOOL=（make 命令行变量优先于 Makefile
   内部赋值）钉死 LOCALBASE 回退分支，LOCALBASE 指向 conan libxml2 包目录，
   构建机（含 CI 机器）系统 libxml2 无法劫持探测结果。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# OS=harmonyos 不在 Makefile.defs 的平台分支内，此处提供 linux 分支等价探测宏。
# 与 kamailio-tls 同族先例一致（对照 OHOS SDK musl 语义 sysroot 实证存在）。
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


class KamailioXmlConan(ConanFile):
    name = "kamailio-xml"
    version = "6.0.6"
    description = ("Kamailio xmlops module: XML operations via libxml2 "
                   "(pseudo-variables $xml for XPath over XML documents in SIP routing)")
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
        self.requires("libxml2/2.15.3.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        libxml2 = self.dependencies["libxml2"].package_folder
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"

        # R33：编译器与头/库搜索路径全部显式注入，不使用未定义的 shell 变量。
        # libxml2 头在包内 include/libxml2 下（经典 libxml2 布局）。
        env = Environment()
        env.define("CC", cc)
        env.define("CPATH", os.path.join(libxml2, "include", "libxml2"))
        env.define("LIBRARY_PATH", f"{libxml2}/lib")

        make_vars = (f"LOCALBASE={libxml2} PKGCFGTOOL= "
                     f"extra_defs='{' '.join(PLATFORM_DEFS)}'")
        with env.vars(self).apply():
            self.run(f"make cfg include_modules=xmlops {make_vars}", cwd=self.source_folder)
            self.run(f"make modules modules=modules/xmlops -j1 {make_vars}",
                     cwd=self.source_folder)

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        module_dir = os.path.join(self.source_folder, "src", "modules", "xmlops")
        dst_dir = os.path.join(self.package_folder, "lib", "kamailio", "modules")
        copy(self, "xmlops.so", src=module_dir, dst=dst_dir)

    def package_info(self):
        # 模块由 kamailio 运行时 loadmodule 加载，不作为链接库供消费者使用
        self.cpp_info.libdirs = ["lib/kamailio/modules"]
        self.cpp_info.libs = []
        self.cpp_info.set_property("kamailio_modules_dir", "lib/kamailio/modules")
