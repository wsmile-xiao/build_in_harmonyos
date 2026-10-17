#!/usr/bin/env python3
"""Conan recipe for libparserutils 0.2.5 (NetSurf parser utility library).

libparserutils 是 NetSurf 浏览器组件库，上游使用 NetSurf 自有构建系统
（Makefile include $(NSSHARED)/makefiles/Makefile.tools），本平台无
netsurf-buildsystem 包。补丁 0001-Makefile.patch 将顶层 Makefile 替换为
standalone Makefile（保留原编译标志、去除 -Werror 以兼容 clang 15，
与 libwapcaplet 0.4.3 历史适配一致）。

构建：make && make install PREFIX=<package_folder>
测试：upstream `make test` 依赖 netsurf-buildsystem 的 testrunner.pl，
本平台用 standalone Makefile 的 test 目标直接编译驱动上游 test/*.c
（make test 34/34 PASS，见 reports/test-report.md）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibparserutilsConan(ConanFile):
    name = "libparserutils"
    version = "0.2.5"
    description = "Lightweight, standards compliant library for parser building (NetSurf project)"
    license = "MIT"
    homepage = "https://www.netsurf-browser.org/projects/libparserutils/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libparserutils is supported only on Linux/OHOS")
        if self.settings.arch != "armv8" and self.settings.os == "OHOS":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)
        # standalone Makefile builds in-source (objects next to sources)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler/linker from Conan conf, never from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        ranlib = compilers.get("ranlib", "llvm-ranlib") if compilers else "llvm-ranlib"
        # R9: -j1 (HMDFS 上 make -j>1 jobserver mkfifo 报 EPERM, E074)
        self.run(f"make CC={cc} AR={ar} RANLIB={ranlib} -j1")

    def package(self):
        # The standalone Makefile install target honours PREFIX/DESTDIR
        self.run(f"make install PREFIX={self.package_folder}")

    def package_info(self):
        self.cpp_info.libs = ["parserutils"]
        self.cpp_info.set_property("cmake_file_name", "LibParserUtils")
        self.cpp_info.set_property("cmake_target_name", "LibParserUtils::parserutils")
        self.cpp_info.set_property("pkg_config_name", "libparserutils")
