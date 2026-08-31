#!/usr/bin/env python3
"""Conan recipe for libwapcaplet 0.4.3.1 (NetSurf string internment library).

libwapcaplet 是 NetSurf 浏览器组件库，上游使用 NetSurf 自有构建系统
（Makefile include $(NSSHARED)/makefiles/Makefile.tools），本平台无
netsurf-buildsystem 包。补丁 0001-Makefile.patch 将顶层 Makefile 替换为
standalone Makefile（保留原编译标志、去除 -Werror 以兼容 clang 15，
与历史适配 notes.md 一致）。

构建：make && make install PREFIX=<package_folder>
测试：上游 `make check` 依赖 libcheck（本平台不可用），探索阶段用自定义
standalone 测试程序 test_lwc.c 覆盖核心 lwc_string_* API（24/24 PASS，
见 notes.md）；test_package 以消费者视角用 CMake 调用真实 API 验证。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibwapcapletConan(ConanFile):
    name = "libwapcaplet"
    version = "0.4.3.1"
    description = "String internment and management tools (NetSurf project)"
    license = "MIT"
    homepage = "https://www.netsurf-browser.org/projects/libwapcaplet/"
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
            raise ConanInvalidConfiguration("libwapcaplet is supported only on Linux/OHOS")
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

        # E120: OHOS SDK lld links libxml2.so.16; inject its lib dir into
        # LD_LIBRARY_PATH so the linker runs on CI workers where the SDK
        # lib path is not on the default loader search path.
        llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        if os.path.isdir(llvm_lib):
            os.environ["LD_LIBRARY_PATH"] = llvm_lib + ":" + os.environ.get("LD_LIBRARY_PATH", "")

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
        self.cpp_info.libs = ["wapcaplet"]
        self.cpp_info.set_property("cmake_file_name", "LibWapcaplet")
        self.cpp_info.set_property("cmake_target_name", "LibWapcaplet::wapcaplet")
        self.cpp_info.set_property("pkg_config_name", "libwapcaplet")
