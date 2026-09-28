#!/usr/bin/env python3
"""Conan recipe — libint 2.13.1 (CMake, 预生成库 tarball).

构建对象为官方 v2.13.1 release 的预生成库 tarball（libint-2.13.1.tgz），
其顶层 CMakeLists.txt 直接构建 Libint2 静态/共享库（target int-static/int）。

依赖：
- eigen/3.4.1：C++11 API（LIBINT2_REQUIRE_CXX_API=ON 默认需要）为 header-only 依赖；
  libint 自带 cmake/modules/FindEigen3.cmake，经 CMAKE_PREFIX_PATH 找到 Conan 注入的 Eigen3。
- Boost 为可选（C++ API 强烈建议），构建时若系统找不到 Boost，
  libint 会解包 external/boost.tar.gz 捆绑副本，无需声明硬依赖。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class LibintConan(ConanFile):
    name = "libint"
    version = "2.13.1"
    description = "A library for the evaluation of molecular integrals of many-body operators over Gaussian functions"
    license = "LGPL-3.0-only"
    homepage = "https://github.com/evaleev/libint"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # C++11 API 依赖的 header-only Eigen（transitive_headers 供消费者一起编译）
        self.requires("eigen/3.4.1", transitive_headers=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 关闭非必需的可选构建：Fortran 接口 / MPFR / Python 绑定
        tc.variables["LIBINT2_ENABLE_FORTRAN"] = "OFF"
        tc.variables["LIBINT2_ENABLE_MPFR"] = "OFF"
        tc.variables["LIBINT2_ENABLE_PYTHON"] = "OFF"
        # 仅编译 C 库 + 预生成的 C++ 源，不启用"编译型 C++ API"（header-only C++ API 保留）
        tc.variables["LIBINT2_REQUIRE_CXX_API_COMPILED"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["int2"]
        self.cpp_info.set_property("cmake_file_name", "libint")
        self.cpp_info.set_property("cmake_target_name", "libint::libint")
