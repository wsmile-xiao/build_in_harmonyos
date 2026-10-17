#!/usr/bin/env python3
"""Conan recipe — fig2sxd 0.24（XFig 转 OpenOffice/LibreOffice Draw 格式工具）.

fig2sxd 将 xfig 格式文件转换为 OpenOffice.org/LibreOffice.org Draw 格式。
构建系统：Makefile
平台：OHOS aarch64 / Linux / macOS
依赖：zlib（压缩输出 .sxd 文件）
"""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class Fig2sxdConan(ConanFile):
    name = "fig2sxd"
    version = "0.24"
    description = "fig2sxd — convert xfig files to OpenOffice.org Draw format"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.com/acfbuerger/fig2sxd"
    url = "https://gitlab.com/acfbuerger/fig2sxd"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 输出 .sxd 为 zip 压缩格式，链接 zlib
        self.requires("zlib/1.3.1.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # OHOS 仅有 clang，CXX 从 settings 推导（Makefile 补丁支持 ?= 覆盖）。
        # Conan 编译器标识符 ≠ 二进制名称：gcc 的 C++ 编译器是 g++（非 gcc++），
        # apple-clang 的 C++ 编译器是 clang++（非 apple-clang++）。
        cxx_map = {"gcc": "g++", "apple-clang": "clang++"}
        cxx = cxx_map.get(str(self.settings.compiler), f"{self.settings.compiler}++")
        zlib = self.dependencies["zlib"]
        include_flags = " ".join(f"-I{d}" for d in zlib.cpp_info.includedirs)
        lib_flags = " ".join(f"-L{d}" for d in zlib.cpp_info.libdirs)
        libs = " ".join(f"-l{lib}" for lib in zlib.cpp_info.libs)
        self.run(f"make all CXX={cxx} INCLUDES='{include_flags}' LIBS='{lib_flags} {libs}'")

    def package(self):
        # Makefile install 目标：PREFIX=/usr，DESTDIR 指定安装根
        self.run(f"make install PREFIX=/usr DESTDIR={self.package_folder}")

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["usr/bin"]
        self.cpp_info.libdirs = []