#!/usr/bin/env python3
"""Conan recipe for LZHAM 1.0.

The upstream release ships several incomplete CMake subprojects.  The
declared patches provide one installable ``lzham`` target, wire the upstream
memory test into CTest, and cover OHOS SDK portability details without
packaging the test executable.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LzhamConan(ConanFile):
    name = "lzham"
    version = "1.0"
    description = "High-ratio lossless data compression library"
    license = "MIT"
    homepage = "https://github.com/richgel999/lzham_codec"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

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
        tc.variables["LZHAM_BUILD_TESTS"] = True
        tc.variables["LZHAM_ANSI_CPLUSPLUS"] = True
        fpic = self.options.get_safe("fPIC")
        if fpic is not None:
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(fpic)
        tc.cache_variables["CMAKE_INSTALL_LIBDIR"] = "lib"

        # Conan's OHOS mapping may produce CMAKE_SYSTEM_NAME=HarmonyOS,
        # which is not known by the CMake installation on the device.  The
        # OHOS compiler/toolchain remains in use; Linux is only the CMake
        # platform module used for this portable C/C++ project.
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # The patched CMake project registers the upstream memory-to-memory
        # test as lzham_upstream_smoke.  Keep this in the package build so
        # conan create records a real upstream test execution.
        self.run("ctest --output-on-failure", cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["lzham"]
        self.cpp_info.set_property("cmake_file_name", "lzham")
        self.cpp_info.set_property("cmake_target_name", "lzham::lzham")
