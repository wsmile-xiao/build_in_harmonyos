#!/usr/bin/env python3
"""Conan recipe — physunits 1.4.0 (CMake header-only library).

physunits (upstream: PhysUnits-CT-Cpp11) 是编译期量纲分析与单位/quantity 运算的
C++11 header-only 库。header-only（CMake INTERFACE library，目标 PhysUnits::PhysUnits），
无任何第三方依赖，库头仅引用 C++ 标准库；上游 lest/ctest 测试在 build() 中实际执行。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PhysunitsConan(ConanFile):
    name = "physunits"
    version = "1.4.0"
    description = ("Compile-time dimensional analysis and unit/quantity manipulation "
                   "in C++11/14 (header-only, PhysUnits-CT-Cpp11)")
    license = "BSL-1.0"
    homepage = "https://github.com/martinmoene/PhysUnits-CT-Cpp11"
    url = ""  # CI fills this
    topics = ("units", "quantity", "dimensional-analysis", "header-only", "cpp11")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["PHYS_UNITS_OPT_BUILD_TESTS"] = True
        tc.variables["PHYS_UNITS_OPT_BUILD_EXAMPLES"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "PhysUnits")
        self.cpp_info.set_property("cmake_target_name", "PhysUnits::PhysUnits")
        self.cpp_info.libs = []
