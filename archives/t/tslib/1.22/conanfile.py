#!/usr/bin/env python3
"""Conan recipe for tslib 1.22 on HarmonyOS.

tslib ships 14 runtime-loadable plugin modules (dlopen'd from
<prefix>/lib/ts) plus 11 diagnostic tools, so the package is built
shared-only: a static libts cannot serve the plugin architecture.
"""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class TslibConan(ConanFile):
    name = "tslib"
    version = "1.22"
    description = "Touchscreen access library with pluggable input/filter modules and diagnostic tools"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/libts/tslib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_env(self):
        # OHOS 编译器（clang/clang++）位于 /data/service/hnp/bin/，不在默认
        # PATH 中；OHOS 适配版 conan 的 AutotoolsToolchain 不把
        # compiler_executables 映射为 CC/CXX，configure 探测
        # aarch64-unknown-linux-gnu-gcc/gcc/cc 全部落空，报
        # "no acceptable C compiler found in $PATH"（参照 adplay/1.9、
        # jack/1.9.22 先例，显式注入 CC/CXX/AR/RANLIB）。
        # 另外 HMDFS 上 profile buildenv 注入的 hnp bash 曾间歇报
        # getcwd 失败污染 autoconf（E386 同族），configure 命令行前缀
        # 强制能力实测干净的 /bin/sh（make 使用 Makefile 内置
        # SHELL=/bin/sh，不受环境变量影响）。
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or "clang++"
        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        bindir = os.path.dirname(cc) if os.path.sep in cc else ""
        ar = compilers.get("ar") or (os.path.join(bindir, "llvm-ar") if bindir else "")
        ranlib = compilers.get("ranlib") or (os.path.join(bindir, "llvm-ranlib") if bindir else "")
        if ar:
            env.define("AR", ar)
        if ranlib:
            env.define("RANLIB", ranlib)
        return env

    def build(self):
        apply_conandata_patches(self)
        configure_args = "--enable-shared --disable-static"
        if self.settings.os == "OHOS":
            # 自带 config.sub/config.guess（2018）不识别 ohos 系统，
            # config.guess 也无法识别 uname -s=HarmonyOS，显式三元组。
            configure_args = (
                "--build=aarch64-unknown-linux-gnu "
                "--host=aarch64-unknown-linux-gnu " + configure_args
            )
        with self._compiler_env().vars(self).apply():
            self.run(
                f'cd "{self.source_folder}" && CONFIG_SHELL=/bin/sh SHELL=/bin/sh '
                f'./configure --prefix="{self.package_folder}" '
                f"{configure_args}",
                env="conanbuild",
            )
            self.run(f'cd "{self.source_folder}" && make -j2', env="conanbuild")
            # 上游无自动化测试套件（见 test_package/MANIFEST.yml 清点证据），
            # automake 的 check 目标是结构性空跑，留档运行。
            self.run(f'cd "{self.source_folder}" && make -j1 check', env="conanbuild")
            self.run(f'cd "{self.source_folder}" && make install', env="conanbuild")

    def package(self):
        rm(self, "*.la", self.package_folder, recursive=True)
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["ts"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["dl"]
        self.cpp_info.set_property("cmake_file_name", "tslib")
        self.cpp_info.set_property("cmake_target_name", "tslib::tslib")
        self.cpp_info.set_property("pkg_config_name", "tslib")
