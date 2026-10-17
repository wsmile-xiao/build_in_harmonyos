#!/usr/bin/env python3
"""Conan recipe — periphery 2.5.0 (CMake)

Upstream: https://github.com/vsergeev/c-periphery (tag v2.5.0)
Note: task platform listed version 3.8.0, which does not exist for the C
library (3.8.0 belongs to the unrelated Swift tool peripheryapp/periphery).
This recipe adapts the latest C release, 2.5.0.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PeripheryConan(ConanFile):
    name = "periphery"
    version = "2.5.0"
    description = ("Library for peripheral I/O (GPIO, LED, PWM, SPI, I2C, MMIO, "
                   "Serial) in Linux")
    license = "MIT"
    homepage = "https://github.com/vsergeev/c-periphery"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external dependencies: only system libc/libpthread/libm.
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        # URL 无 .tar.gz 扩展名（codeload /tar.gz/ 路径），需 filename 指定以便 conan 正确解压
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="c-periphery-2.5.0.tar.gz")

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream CMakeLists builds a SHARED library (add_library without
        # STATIC/SHARED). periphery is NOT a system-name library (libperiphery
        # has no /lib or /lib64 collision), so default shared is fine (R26
        # does not apply).
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Hardware-dependent test programs are built only for developer
        # hardware bring-up; the consumer test in test_package/ covers the
        # public API availability for the packaged library.
        tc.variables["BUILD_TESTS"] = "OFF"
        if self.options.shared:
            # E330: OHOS is an unknown CMake platform — without these flags CMake
            # skips SONAME/versioned-symlink handling for the shared lib and
            # packages an unversioned libperiphery.so with no DT_SONAME
            # (CI L5a/L5c fail). Force the -Wl,-soname flag with the plain
            # unversioned name: DT_SONAME=libperiphery.so (relocatable, no
            # versioned symlinks to create), package stays a single real .so.
            tc.cache_variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"
            tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
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
        self.cpp_info.libs = ["periphery"]
        self.cpp_info.includedirs = ["include/periphery", "include"]
        if self.settings.os in ["Linux", "OHOS"]:
            self.cpp_info.system_libs = ["pthread"]
