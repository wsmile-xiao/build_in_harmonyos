#!/usr/bin/env python3
"""Conan recipe for libjuice 1.6.0 — UDP Interactive Connectivity Establishment (ICE) library.

CMake-based build. Pure C, C11. Optional Nettle integration is disabled
(USE_NETTLE=OFF), only Threads (system) is required. Shared library target
'juice' is installed along with headers and the CMake package config.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, get, export_conandata_patches


class LibjuiceConan(ConanFile):
    name = "libjuice"
    version = "1.6.0"
    description = "UDP Interactive Connectivity Establishment (ICE) library"
    license = "MPL-2.0"
    homepage = "https://github.com/paullouisageneau/libjuice"
    url = ""  # CI fills this

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
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
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
        self.cpp_info.libs = ["juice"]
        self.cpp_info.set_property("cmake_file_name", "libjuice")
        self.cpp_info.set_property("cmake_target_name", "libjuice::libjuice")
        self.cpp_info.set_property("pkg_config_name", "libjuice")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]