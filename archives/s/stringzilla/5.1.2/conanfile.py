#!/usr/bin/env python3
"""Conan recipe for StringZilla 5.1.2 C API."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class StringzillaConan(ConanFile):
    name = "stringzilla"
    version = "5.1.2"
    description = "SIMD-accelerated, length-bounded string algorithms with a stable C API."
    license = "Apache-2.0"
    homepage = "https://github.com/ashvardanian/StringZilla"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("string", "simd", "c", "utf8")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("forkunion/3.0.2")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def validate(self):
        if not self.options.shared:
            raise ConanInvalidConfiguration("StringZilla 5.1.2 recipe currently provides the upstream shared core only")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["STRINGZILLA_INSTALL"] = "ON"
        tc.variables["STRINGZILLA_BUILD_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["STRINGZILLA_BUILD_TEST"] = "ON"
        tc.variables["STRINGZILLA_BUILD_BENCHMARK"] = "OFF"
        tc.variables["STRINGZILLAS_BUILD_SHARED"] = "OFF"
        tc.variables["STRINGZILLA_BUILD_CUDA"] = "OFF"
        tc.variables["STRINGZILLA_USE_SANITIZERS"] = "OFF"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.libs = ["stringzilla_shared"] if self.options.shared else []
        self.cpp_info.defines = ["SZ_DYNAMIC_DISPATCH=1"]
        self.cpp_info.set_property("cmake_file_name", "stringzilla")
        self.cpp_info.set_property("cmake_target_name", "stringzilla::shared")
        self.cpp_info.set_property("pkg_config_name", "stringzilla")
