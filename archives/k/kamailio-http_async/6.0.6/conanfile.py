#!/usr/bin/env python3
"""Kamailio http_async_client 模块（http_async_client.so）Conan 配方 — HarmonyOS PC / aarch64。

打包口径（参照同族先例 archives/k/kamailio-lua/6.0.6、kamailio-uuid/6.0.6、
kamailio-tls/6.0.6）：
  - 取官方 kamailio 6.0.6 源码包全量构建，仅编译打包 http_async_client 模块
    （积分赛任务 kamailio-http_async 对应 kamailio 源码树内的 http_async_client
     模块：6.0.6 源码包无名为 http_async 的模块目录）
  - 不依赖 kamailio 本体包（模块 .so 由 kamailio 运行时 loadmodule 加载）

构建体系：kamailio 6.0.6 自带经典 Makefile 体系（src/Makefile + Makefile.defs）
  make cfg include_modules=http_async_client
  make modules modules=modules/http_async_client
  模块 Makefile 经 pkg-config libcurl 探测 CURLLIBS，回退 -lcurl -levent

平台差异（详见同目录 notes.md，均与 kamailio-lua 同源实证）：
1) 平台探测宏：OS=harmonyos 不在 Makefile.defs 平台分支内，core 头直接 #error，
   经 extra_defs 注入 linux 分支等价宏集（与 kamailio-lua 完全一致）
2) libcurl/libevent 探测：显式 LOCALBASE 指向 conan 依赖目录 + PKG_CONFIG_PATH，
   构建机系统库无法劫持；静态链接规避 musl 无 rpath 的运行时加载问题
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# OS=harmonyos 不在 Makefile.defs 的平台分支内，此处提供 linux 分支等价探测宏
# （与 kamailio-lua/6.0.6 同族先例完全一致，均对照 OHOS SDK sysroot 头文件实证）
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


class KamailioHttpAsyncConan(ConanFile):
    name = "kamailio-http_async"
    version = "6.0.6"
    description = ("Kamailio http_async_client module: asynchronous HTTP queries "
                   "from the SIP routing configuration (libcurl + libevent based)")
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

    def requirements(self):
        # 模块 CMake/Makefile 期望 CURL::libcurl + event::event（-lcurl -levent）。
        # W0 实测制品仓：curl/8.15.0.1（配方名 curl）、libevent/2.1.12。
        # 注：采用制品仓默认共享变体——静态 curl 触发 openssl 全量重编译
        # （本机实测两次超时/僵挂且 curl 配方自带 1679 项自测，成本不可控）；
        # 共享依赖由 conan install 随包解析（消费者 LD_LIBRARY_PATH 注入，
        # sems-dsm 已验证模式），check_module 断言按共享模型校验
        self.requires("curl/8.15.0.1")
        self.requires("libevent/2.1.12")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"{self.ref} supports Linux/OHOS only")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        curl_pkg = self.dependencies["curl"]  # conan dependency lookup, not external curl
        lev = self.dependencies["libevent"]
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"

        # R33：编译器与头/库搜索路径全部显式注入，不使用未定义的 shell 变量
        env = Environment()
        env.define("CC", cc)
        # 模块 Makefile: pkg-config libcurl → curl-config → 回退 -lcurl -levent。
        # PKG_CONFIG_PATH 指向 conan 依赖的 .pc（构建机系统 curl 无法劫持探测）；
        # CPATH/LIBRARY_PATH 双兜底（musl 无 rpath 场景静态链接）
        pc_paths = []
        for dep in (curl_pkg, lev):
            pc = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pc):
                pc_paths.append(pc)
        if pc_paths:
            env.define("PKG_CONFIG_PATH", os.pathsep.join(pc_paths))
        env.define("CPATH", os.pathsep.join(
            [os.path.join(curl_pkg.package_folder, "include"),
             os.path.join(lev.package_folder, "include")]))
        env.define("LIBRARY_PATH", os.pathsep.join(
            [os.path.join(curl_pkg.package_folder, "lib"),
             os.path.join(lev.package_folder, "lib")]))

        make_vars = (f"LOCALBASE={curl_pkg.package_folder} BUILDER= "
                     f"extra_defs='{' '.join(PLATFORM_DEFS)}'")
        with env.vars(self).apply():
            self.run(f"make cfg include_modules=http_async_client {make_vars}",
                     cwd=self.source_folder)
            self.run(f"make modules modules=modules/http_async_client -j1 {make_vars}",
                     cwd=self.source_folder)

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        module_dir = os.path.join(self.source_folder, "src", "modules", "http_async_client")
        dst_dir = os.path.join(self.package_folder, "lib", "kamailio", "modules")
        copy(self, "http_async_client.so", src=module_dir, dst=dst_dir)
        # 模块文档（消费者配置参考）
        copy(self, "README", src=module_dir,
             dst=os.path.join(self.package_folder, "share", "kamailio", "doc",
                              "http_async_client"))

    def package_info(self):
        # 模块由 kamailio 运行时 loadmodule 加载，不作为链接库供消费者使用
        self.cpp_info.libdirs = ["lib/kamailio/modules"]
        self.cpp_info.libs = []
        self.cpp_info.set_property("kamailio_modules_dir", "lib/kamailio/modules")
