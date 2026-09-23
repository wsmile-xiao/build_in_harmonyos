#!/usr/bin/env python3
"""Conan recipe — nvtx 3.6.0-c-cpp (NVIDIA Tools Extension, C/C++ APIs).

NVTX C/C++ is a header-heavy instrumentation API: `nvtx3-c` and `nvtx3-cpp`
are CMake INTERFACE targets (headers only), and `nvtxw3-loader` is a small
static library (src/nvtxw3_loader.c) that implements the NVTXW writer
backend loader (nvtxwLoad / nvtXwUnload) on top of dlopen/dlsym.

Upstream CMake installs headers + nvtx3 cmake package files + the three
targets. No third-party dependencies (only ${CMAKE_DL_LIBS}).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class NvtxConan(ConanFile):
    name = "nvtx"
    version = "3.6.0-c-cpp"
    description = "NVIDIA Tools Extension (NVTX) C and C++ APIs — instrumentation/profiling annotation headers"
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://github.com/NVIDIA/NVTX"
    url = "https://github.com/NVIDIA/NVTX"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 CMakeLists 声明 cmake_minimum_required(3.19)（>3.5），无需
        # CMAKE_POLICY_VERSION_MINIMUM；保持默认 standalone 安装规则开启。
        tc.variables["NVTX3_INSTALL"] = "ON"
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
        # 上游导出目标: nvtx3::nvtx3-c / nvtx3::nvtx3-cpp / nvtx3::nvtxw3-loader
        # 包内唯一编译产物为静态库 nvtxw3-loader（nvtxwLoad/nvtxwUnload）。
        self.cpp_info.set_property("cmake_file_name", "nvtx3")
        self.cpp_info.set_property("cmake_build_modules", [])

        # nvtx3-c: C API 头文件接口目标 (INTERFACE)
        self.cpp_info.components["c"].set_property("cmake_target_name", "nvtx3::nvtx3-c")
        # nvtx3-cpp: C++ API 头文件接口目标 (INTERFACE, 依赖 nvtx3-c)
        self.cpp_info.components["cpp"].set_property("cmake_target_name", "nvtx3::nvtx3-cpp")
        self.cpp_info.components["cpp"].requires = ["c"]
        # nvtxw3-loader: 静态库 (nvtxwLoad/nvtxwUnload, dlopen/dlsym, 依赖 nvtx3-c 头文件)
        self.cpp_info.components["loader"].libs = ["nvtxw3-loader"]
        self.cpp_info.components["loader"].set_property("cmake_target_name", "nvtx3::nvtxw3-loader")
        self.cpp_info.components["loader"].requires = ["c"]
