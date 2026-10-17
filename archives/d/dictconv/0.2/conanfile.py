#!/usr/bin/env python3
"""Conan recipe — dictconv 0.2 (HarmonyOS PC / aarch64-linux-ohos).

dictconv 是 2007 年的命令行词典格式转换工具，上游同时带 autotools 与 CMake 两套
构建脚本。本配方走上游自带的 CMake 路径，原因：
  * autotools：configure 携带 2006 年版 config.guess，无法识别 HarmonyOS
    （`uname -p` 返回 unknown → configure rc=1）；且 aclocal.m4 的 AM_PATH_XML2
    用 AC_TRY_RUN 探测 libxml2，交叉编译下无法运行；
  * CMake：上游 CMakeLists 只做 FIND_PATH/FIND_LIBRARY，交叉编译时由本配方用
    cache_variables 直接把 Conan 包内的头文件/库路径喂进去，无需改上游脚本。

依赖：
  * libxml2 — 解析/生成 FreeDict TEI (.tei) 词条，共享库（OHOS 系统目录无同名库，
    R26 系统同名库隔离规则不适用，运行时由 conanrun 提供 libxml2.so.16）；
  * zlib    — Sdictionary (.dct) / StarDict (.dict.dz) 解压，静态库（R26）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class DictconvConan(ConanFile):
    name = "dictconv"
    version = "0.2"
    description = "Dictionary file format converter (Babylon/Freedict/Sdictionary/StarDict)"
    license = "GPL-2.0-or-later"
    homepage = "http://dictconv.sourceforge.net/"
    url = "https://ftp.debian.org/debian/pool/main/d/dictconv/"  # 上游站点已下线，源码取 Debian pool 原始 tarball

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libxml2/2.15.3.1")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 src/CMakeLists.txt 用 FIND_PATH(XML2_INCLUDE_DIR ...) / FIND_LIBRARY(XML2_LIBRARY ...)
        # 在 /usr/local、/usr 下找 libxml2，交叉编译时找不到；FIND_* 一旦发现同名缓存
        # 变量就直接采用，因此这里从依赖包 cpp_info 计算路径，避免改动上游构建脚本。
        libxml2 = self.dependencies["libxml2"]
        tc.cache_variables["XML2_INCLUDE_DIR"] = os.path.join(
            libxml2.package_folder, libxml2.cpp_info.includedirs[0]
        )
        tc.cache_variables["XML2_LIBRARY"] = os.path.join(
            libxml2.package_folder, libxml2.cpp_info.libdirs[0], "libxml2.so"
        )
        zlib = self.dependencies["zlib"]
        # zlib 走静态链接（R26：不动态链接系统同名库；OHOS sysroot 内有 libz.so），
        # 显式指向依赖包内的 libz.a，避免 FIND_PACKAGE(ZLIB) 在混合环境下选到共享库。
        tc.cache_variables["ZLIB_INCLUDE_DIR"] = os.path.join(
            zlib.package_folder, zlib.cpp_info.includedirs[0]
        )
        tc.cache_variables["ZLIB_LIBRARY"] = os.path.join(
            zlib.package_folder, zlib.cpp_info.libdirs[0], "libz.a"
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
