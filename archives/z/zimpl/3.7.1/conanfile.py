#!/usr/bin/env python3
"""Conan recipe for zimpl 3.7.1 — Zuse Institute Mathematical Programming Language.

ZIMPL is a little language to translate the mathematical model of a problem into
a linear or (mixed-)integer mathematical program expressed in .lp or .mps file
format readable by LP/MIP solvers.

Build system: CMake (project ZIMPL, LANGUAGES C, C99)
Library output: libzimpl.a / libzimpl-pic.a (static)
Binary output: bin/zimpl (command-line translator)
Dependencies: gmp/6.3.0.1 (REQUIRED), zlib/1.3.2 (optional, enabled by default)
Build tools: bison >= 2.4.0 (REQUIRED, generates mmlparse2.c), flex (REQUIRED, generates mmlscan.c)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ZimplConan(ConanFile):
    name = "zimpl"
    version = "3.7.1"
    description = "ZIMPL - Zuse Institute Mathematical Programming Language: translate mathematical models into LP/MPS files"
    license = "LGPL-3.0"
    homepage = "https://zimpl.zib.de/"
    url = "https://github.com/scipopt/zimpl"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gmp/6.3.0.1")
        self.requires("zlib/1.3.2")

    def build_requirements(self):
        self.tool_requires("bison/3.8.2")
        self.tool_requires("flex/2.6.4.2")
        # bison 运行时需要 m4 宏库（BISON_PKGDATADIR 重定向），m4 作为工具依赖提供
        self.tool_requires("m4/1.4.19")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # zimpl bundles cmake/Modules/FindGMP.cmake which honours GMP_DIR
        gmp = self.dependencies["gmp"]
        tc.cache_variables["GMP_DIR"] = gmp.package_folder
        # zimpl 是纯 C 项目，源码只用 <gmp.h> 的 C 接口，无任何 gmpxx 引用；
        # FindGMP 默认把 libgmp 与 libgmpxx 都加入 GMP_LIBRARIES，链入 gmpxx
        # 会引入对 libc++_shared.so 的运行时依赖（OHOS 上执行报 symbol not found）。
        # 预设 GMPXX_LIBRARY 为空串阻止 find_library 搜索，GMP_LIBRARIES 只剩 libgmp。
        tc.cache_variables["GMPXX_LIBRARY"] = ""
        # zimpl uses find_package(ZLIB); point directly at the conan zlib package
        zlib = self.dependencies["zlib"]
        tc.cache_variables["ZLIB_INCLUDE_DIR"] = os.path.join(zlib.package_folder, "include")
        tc.cache_variables["ZLIB_LIBRARY"] = os.path.join(zlib.package_folder, "lib", "libz.a")
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        tc.variables["ZLIB"] = "ON"
        # E298: OHOS 直跑环境（aarch64 主机跑 OHOS 二进制）动态加载时
        # LD_LIBRARY_PATH 不生效，只能靠 DT_RUNPATH 定位依赖库。
        # 让 install 阶段保留链接时的 rpath（指向 conan 依赖 lib 目录），
        # 否则 CMake install 重写/移除 RUNPATH 会破坏 ELF 结构导致 execve EPERM。
        tc.variables["CMAKE_INSTALL_RPATH_USE_LINK_PATH"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # bison 编译内置 pkgdatadir 为 /share/bison（--prefix= 导致），
        # 必须重定向 BISON_PKGDATADIR 到 conan 包内实际位置（同仓库 ball 配方做法）
        bison_pkg = self.dependencies.build["bison/3.8.2"].package_folder
        m4_pkg = self.dependencies.build["m4/1.4.19"].package_folder
        os.environ["BISON_PKGDATADIR"] = os.path.join(bison_pkg, "share", "bison")
        os.environ["M4"] = os.path.join(m4_pkg, "bin", "m4")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # CMake install 会把链接期 RUNPATH 的尾冒号规范化掉
        # （/path/lib: → /path/lib，尾冒号=继续搜索默认路径）。
        # OHOS loader 校验 RUNPATH 缺少尾冒号的 ELF 时 execve 返回
        # EPERM（Operation not permitted）。用 build 目录原始二进制
        # 覆盖 install 产物，保留链接期完整 RUNPATH。
        from conan.tools.files import copy
        src_bin = os.path.join(self.build_folder, "bin", "zimpl")
        if os.path.isfile(src_bin):
            copy(self, "zimpl", src=os.path.dirname(src_bin),
                 dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "zimpl")
        self.cpp_info.set_property("cmake_target_name", "zimpl::zimpl")
        self.cpp_info.set_property("pkg_config_name", "zimpl")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = ["zimpl"]
