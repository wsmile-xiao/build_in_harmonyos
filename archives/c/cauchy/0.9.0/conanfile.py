#!/usr/bin/env python3
"""Conan recipe — cauchy 0.9.0 (Cauchy Mathematic Compiler 库 + cauchymc 工具).

Cauchy 提供将 MATLAB/Octave 脚本翻译为 C++（Eigen 后端）的库与 CLI 工具。
平台：OHOS aarch64 / Linux
依赖：eigen（header-only）
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, copy


class CauchyConan(ConanFile):
    name = "cauchy"
    version = "0.9.0"
    description = "Cauchy - MATLAB/Octave to C++ (Eigen) 编译库与 cauchymc 工具"
    license = "LGPL-2.1-or-later"
    homepage = "https://bitbucket.org/cyrille/cauchy"
    url = ""
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    exports_sources = "patches/*"

    def requirements(self):
        self.requires("eigen/3.4.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # 静态优先（OHOS 默认）；Build with tests off; internal minimal cmake
        tc.variables["CAUCHY_BUILD_TESTS"] = "OFF"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        eig = self.dependencies["eigen"]
        tc.variables["EIGEN3_INCLUDE_DIR"] = os.path.join(
            eig.package_folder, "include", "eigen3")
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 额外安装库的头文件（上游 CMake 只 install Runtime/m2mml 头）
        copy(self, "*.h", src=os.path.join(self.source_folder, "Cauchy"),
             dst=os.path.join(self.package_folder, "include", "Cauchy"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "Runtime", "Cauchy"),
             dst=os.path.join(self.package_folder, "include", "Cauchy"))

    def package_info(self):
        self.cpp_info.libs = ["Cauchy", "CauchyXUnit", "m2mml"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
