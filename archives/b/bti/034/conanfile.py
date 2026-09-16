#!/usr/bin/env python3
"""Conan recipe for bti 034 (autotools, command line tool).

bti — "bash twitter/identi.ca ididocy"：把标准输入/bash 命令输出直接发成
twitter 或 identi.ca 的状态更新。上游：https://github.com/gregkh/bti
（发布 tarball 由项目主页指向 kernel.org）。

HarmonyOS OHOS aarch64 适配要点（补丁编号以 patches/ 与 conandata.yml 为准）：
- 发布 tarball 自带预生成 configure，配方不跑 autoreconf：CI worker 的
  PATH 没有 automake/aclocal，走 autoreconf 会稳定失败（W§4.2 已知假绿面）。
- HMDFS：config.status 以 umask 077 建临时目录 → 0700 目录在 setgid hmdfs
  挂载上对构建用户不可写（E114/E129 同族，a52dec/liboauth 先例）。补丁 0003
  放宽为 022；发布 tarball 只有预生成 configure，故补丁打在 configure 本体上。
- json-c 0.13 起移除 is_error 宏，补丁 0002 把 3 处调用改为显式 NULL 比较
  （与 Debian bti 034-6 replace_removed_is_error.patch 同口径）。
- OHOS 没有 /bin/bash，bin_SCRIPTS 安装的 bti-shrink-urls 直接执行报
  "bad interpreter"（rc=126），补丁 0001 把 shebang 改为 #!/bin/sh。
- 依赖图冲突：已发布的 liboauth/1.0.3 钉 openssl/1.1.1w，已发布的
  curl/8.15.0 钉 openssl/3.5.6.1，二者在 openssl 上硬冲突（各自只发布了一个
  package_id）。本配方在消费侧用 override 统一到 openssl/3.5.6.1，代价是
  liboauth 在 conan create --build=missing 时从源码重建（liboauth 为静态库，
  设备实测可编；见 notes.md）。
"""
from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class BtiConan(ConanFile):
    name = "bti"
    version = "034"
    description = ("Command line client that pipes stdin/bash output to "
                   "twitter or identi.ca as a status update")
    license = "GPL-2.0-or-later"
    homepage = "https://gregkh.github.io/bti/"
    url = "https://github.com/gregkh/bti"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure 用 PKG_CHECK_MODULES 探测这 5 个模块；readline 只在上游
        # 运行期通过 dlopen 尝试加载（可选，不进构建依赖链）。
        self.requires("liboauth/1.0.3")
        self.requires("curl/8.15.0")
        self.requires("libxml2/2.15.3")
        self.requires("json-c/0.17")
        self.requires("pcre/8.45")
        # 统一 openssl 版本：liboauth/1.0.3 pin openssl/1.1.1w、curl/8.15.0 pin
        # openssl/3.5.6.1，不 override 会在图计算阶段直接 Version conflict。
        # 取 3.5.6.1 是因为它只需重建 liboauth（静态、体量极小），而取 1.1.1w
        # 需要重建 curl。仓库内 override=True 已有 85 处先例。
        self.requires("openssl/3.5.6.1", override=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # configure 的 PKG_CHECK_MODULES 模块名与包名不一致：包 liboauth 提供
        # 模块 oauth、包 pcre 提供模块 libpcre，其余（libcurl/libxml-2.0/
        # json-c）PkgConfigDeps 默认名即正确。
        deps = PkgConfigDeps(self)
        deps.set_property("liboauth", "pkg_config_name", "oauth")
        deps.set_property("pcre", "pkg_config_name", "libpcre")
        deps.generate()
        tc = AutotoolsToolchain(self)
        # PkgConfigDeps 把 .pc 写在 generators_folder，但 conanbuild 环境不会自动
        # 注入 PKG_CONFIG_PATH；PKG_CONFIG_PATH 由 pkg.m4 的 AC_ARG_VAR 声明，
        # 可直接作为 configure 变量传入（abiword-plugin-eml 同法）。
        # 不把 PKG_CONFIG_PATH 指向依赖包自带的 lib/pkgconfig：包内 .pc 的
        # prefix 固化了打包机路径（W§5.1）。
        tc.configure_args.append(
            "PKG_CONFIG_PATH={}".format(self.generators_folder))
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # 设备默认单作业（W§A3）；bti 只有 3 个 C 文件，-j1 足够。
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()

    def package_info(self):
        # 纯可执行包：只交付 bin/（bti 与 bti-shrink-urls）+ share/man。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
