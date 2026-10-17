#!/usr/bin/env python3
"""Conan recipe — muparser 2.3.5 (CMake project).

muparser: C++ math expression parser library (beltoforion/muparser).
No third-party dependencies. Build via CMake, install headers + lib + pkg-config.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MuparserConan(ConanFile):
    name = "muparser"
    version = "2.3.5"
    description = "muparser is a high performance mathematical expression parser library."
    license = "MIT"
    homepage = "https://github.com/beltoforion/muparser"
    url = "https://github.com/beltoforion/muparser"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 上游默认 ENABLE_OPENMP=ON 需 find_package(OpenMP REQUIRED)，CI 无 OpenMP -> 关闭
        tc.variables["ENABLE_OPENMP"] = "OFF"
        # 库包不需要构建样例/示例
        tc.variables["ENABLE_SAMPLES"] = "OFF"
        # 构建阶段不启用 CTest（上游测试在任务阶段单独运行并记录台账）
        tc.variables["BUILD_TESTING"] = "OFF"
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
        self.cpp_info.libs = ["muparser"]
        self.cpp_info.set_property("cmake_target_name", "muparser::muparser")
