#!/usr/bin/env python3
"""Conan recipe for backward-cpp 1.6 — CMake header-only stacktrace library.

backward-cpp prints readable stack traces on error / in debug mode.
Build: CMake, header-only (installs backward.hpp + BackwardConfig.cmake).

OHOS adaptations (patches/):
- CMakeLists.txt: bump cmake_minimum_required 3.0 -> 3.5 (CMake 4.x compat)
- backward.hpp: dlfcn.h must be included with _GNU_SOURCE so Dl_info is exposed
- test/_test_main.cpp: use __progname instead of glibc-only program_invocation_name
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BackwardCppConan(ConanFile):
    name = "backward-cpp"
    version = "1.6"
    description = "A beautiful stack trace pretty printer for C++"
    license = "MIT"
    homepage = "https://github.com/bombela/backward-cpp"
    url = "https://github.com/bombela/backward-cpp"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # backward-cpp is header-only with no external dependencies
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "backward-cpp")
        self.cpp_info.set_property("cmake_target_name", "backward-cpp::backward-cpp")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("dl")
