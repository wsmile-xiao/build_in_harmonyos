#!/usr/bin/env python3
"""Conan recipe — charls 2.4.3 (CMake C++14 JPEG-LS library).

charls 是 JPEG-LS 无损/近无损图像压缩标准的 C++ 实现,
无第三方依赖, 使用 CMake 构建为静态/动态库。
"""
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class CharlsConan(ConanFile):
    name = "charls"
    version = "2.4.3"
    description = "C++ JPEG-LS 无损/近无损图像压缩库"
    license = "BSD-3-Clause"
    homepage = "https://github.com/team-charls/charls"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake does not recognize OHOS as a target platform
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # R26: 默认静态库
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 禁用测试/示例/fuzz, 加速构建
        tc.variables["CHARLS_BUILD_TESTS"] = "OFF"
        tc.variables["CHARLS_BUILD_FUZZ_TEST"] = "OFF"
        tc.variables["CHARLS_BUILD_SAMPLES"] = "OFF"
        tc.variables["CHARLS_INSTALL"] = "ON"
        tc.generate()

        # 修复编译器路径: profile 中的路径在本地可能不存在
        cc = shutil.which("clang") or "clang"
        cxx = shutil.which("clang++") or "clang++"
        toolchain_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if os.path.exists(toolchain_file):
            with open(toolchain_file, "r") as f:
                content = f.read()
            content = re.sub(
                r'set\(CMAKE_C_COMPILER\s+"[^"]+"\)',
                f'set(CMAKE_C_COMPILER "{cc}")',
                content
            )
            content = re.sub(
                r'set\(CMAKE_CXX_COMPILER\s+"[^"]+"\)',
                f'set(CMAKE_CXX_COMPILER "{cxx}")',
                content
            )
            with open(toolchain_file, "w") as f:
                f.write(content)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["charls"]
        if not self.options.shared:
            self.cpp_info.defines.append("CHARLS_STATIC")
