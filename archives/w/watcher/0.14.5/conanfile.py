#!/usr/bin/env python3
"""Conan recipe — watcher 0.14.5 (CMake filesystem watcher library)."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class WatcherConan(ConanFile):
    name = "watcher"
    version = "0.14.5"
    description = "Cross-platform filesystem watcher library and CLI tools"
    license = "MIT"
    homepage = "https://github.com/e-dant/watcher"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BUILD_SAN"] = False
        tc.variables["BUILD_ASAN"] = False
        tc.variables["BUILD_MSAN"] = False
        tc.variables["BUILD_TSAN"] = False
        tc.variables["BUILD_UBSAN"] = False
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
        self.cpp_info.libs = ["watcher-c"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.set_property("cmake_file_name", "watcher")
        self.cpp_info.set_property("cmake_target_name", "watcher::watcher")
        self.cpp_info.set_property("pkg_config_name", "watcher-c")
