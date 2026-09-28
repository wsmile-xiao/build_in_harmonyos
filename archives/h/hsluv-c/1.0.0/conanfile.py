#!/usr/bin/env python3
# 权限: 本配方在 OHOS PC 平台适配使用
"""Conan recipe — hsluv-c 1.0.0 (pure C colour space conversion library).

Human-friendly HSL (HSLuv / HPLuv) color space conversion library.
Pure C99, single translation unit, only external dependency is libm.
Upstream CMake builds a static library and an acutest-based test harness
but ships no install rules, so the recipe packages the static lib and the
public header manually (R26: static-only delivery).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, export_conandata_patches, apply_conandata_patches, get
from conan.errors import ConanInvalidConfiguration

required_conan_version = ">=2.0"


class HsluvCConan(ConanFile):
    name = "hsluv-c"
    version = "1.0.0"
    package_type = "library"

    description = "HSLuv / HPLuv colour space conversion library (C99)"
    homepage = "https://github.com/hsluv/hsluv-c"
    license = "MIT"
    url = "https://github.com/hsluv/hsluv-c"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        # Upstream only produces a static library (add_library STATIC, no shared rule).
        if self.options.shared:
            raise ConanInvalidConfiguration("hsluv-c is static-only")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler/flags come from the Conan toolchain, never from bare shell env vars.
        cmake = CMake(self)
        # CMake >= 4.x removed support for cmake_minimum_required < 3.5; upstream requires 3.1.
        # Pass as a configure -D (command line) so it is evaluated before CMakeLists.txt.
        cmake.configure(variables={"HSLUV_C_TESTS": "ON", "BUILD_SHARED_LIBS": "OFF",
                                   "CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()
        # Run the upstream acutest harness inside W3 (real upstream test evidence).
        cmake.test()

    def package(self):
        copy(self, "hsluv.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libhsluv-c.a", src=os.path.join(self.build_folder, "src"),
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["hsluv-c"]
        if self.settings.os != "Windows":
            self.cpp_info.system_libs = ["m"]