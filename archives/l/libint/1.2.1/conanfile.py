#!/usr/bin/env python3
"""Conan recipe for libint 1.2.1 (Libint1 系列) — CMake（Psi4 移植的构建路径）。

libint 1.x 是量子化学中的高斯函数两算符分子积分库（Edward F. Valeev）。
本配方适配的是官方 GitHub tag `release-1-2-1` 的 **Libint1 源码树**
（Debian/Ubuntu `libint_1.2.1.orig.tar.gz` 与此 tag 逐字节一致，同一 sha256）。

与 libint2（导出的预生成库 tarball）不同，Libint1 的 release 源码树**不含**
预生成积分核：`src/bin/libint/build_libint.c` 是 C 写的生成器
（libint_compiler），构建时由 CMake 的 `ExternalProject` 先编译并运行它，
生成 `src/lib/libint/` 的库源码（.+libderiv），再编译出静态库
`libint.a` / `libderiv.a`。

因此本配方选用上游 CMake 路径（Psi4 移植，README_CMake.md 推荐），
而不是 autotools 路径：CMake 路径**不需要 perl/autotools**（configure.ac 的
`AC_CHECK_PROG(PERL)` + `bin/objectdir.pl` 仅 autotools 编译路径需要；
CMake 生成器是纯 C），对 OHOS 更稳。

OHOS 适配要点：
  1. 上游 CMakeLists 的各子项目把 `DESTINATION ${CMAKE_INSTALL_PREFIX}` 在
     configure 期固化成绝对路径（ExternalProject 阶段装到
     `${build}/stage${prefix}`）。因此 `generate()` 里把
     `CMAKE_INSTALL_PREFIX` 指定为该配方的自包含 staging 前缀
     `${build_folder}/_install`，`package()` 里 `cmake --install .`（无
     --prefix，用缓存的 prefix）后把 `_install/*` 拷进 package_folder。
  2. `ENABLE_XHOST=OFF`：上游默认 ON 会加 `-march=native`，去平台相关优化
     保证可复现。
  3. 默认静态库（R26 非系统同名库，静态避免 OHOS RPATH/依赖链问题）；
     默认 `MAX_AM_ERI=4`（LIBINT_MAX_AM=5，覆盖到 d 壳层，构建量适中），
     可用 `-o libint/*:max_am_eri=N` 上调。
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibintConan(ConanFile):
    name = "libint"
    version = "1.2.1"
    description = ("A library for the evaluation of molecular integrals of two-body "
                   "operators over Gaussian functions (Libint1 series)")
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/evaleev/libint"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("quantum-chemistry", "molecular-integrals", "gaussian-integrals")

    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"

    options = {
        # MAX_AM_ERI：库支持的最大角动量（Psi4 口径），与 LIBINT_MAX_AM 关系见
        # README_CMake.md 表格：MAX_AM_ERI=N → LIBINT_MAX_AM=N+1。
        "max_am_eri": [3, 4, 5, 6, 7, 8],
    }
    default_options = {"max_am_eri": 4}

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游把 DESTINATION ${CMAKE_INSTALL_PREFIX} 等固化成绝对路径，故显式
        # 指定到自包含 staging 前缀，package() 里统一拷入 package_folder。
        # （不用 conan 的 cmake.install() 默认 --prefix，因为无法覆盖已固化的绝对 DESTINATION）
        tc.variables["CMAKE_INSTALL_PREFIX"] = os.path.join(self.build_folder, "_install")
        tc.variables["MAX_AM_ERI"] = str(self.options.max_am_eri)
        tc.variables["ENABLE_XHOST"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["BUILD_FPIC"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # 用缓存的 CMAKE_INSTALL_PREFIX（build_folder/_install）安装：
        # 绝对 DESTINATION 与相对配置都落到 _install，再整体拷入包目录，
        # 得到完整自包含布局（include/ + lib/libint.a,libderiv.a + share/cmake/Libint）。
        self.run("cmake --install .", cwd=self.build_folder, env="conanbuild")
        install_prefix = os.path.join(self.build_folder, "_install")
        copy(self, "*", src=install_prefix, dst=self.package_folder)

    def package_info(self):
        # 主库 libint.a（ERI）。libderiv.a（导数积分）也会随包安装到 lib/，
        # 需要时消费者可自行链接。
        self.cpp_info.set_property("cmake_file_name", "Libint")
        self.cpp_info.set_property("cmake_target_name", "Libint::int")
        self.cpp_info.libs = ["int"]
