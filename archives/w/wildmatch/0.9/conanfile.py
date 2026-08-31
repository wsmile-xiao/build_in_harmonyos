#!/usr/bin/env python3
"""Conan recipe for wildmatch — CMake project.

wildmatch is a BSD-licensed C/C++ library for git/rsync-style pattern matching.
"""
from conan import ConanFile
import os
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class WildmatchConan(ConanFile):
    name = "wildmatch"
    version = "0.9"
    description = "A BSD-licensed C/C++ library for git/rsync-style pattern matching"
    license = "BSD-2-Clause"
    homepage = "https://github.com/davvid/wildmatch"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["BUILD_TESTING"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # C library
        self.cpp_info.components["wildmatch_c"].libs = ["wildmatch"]
        self.cpp_info.components["wildmatch_c"].includedirs = ["include"]
        
        # C++ library
        self.cpp_info.components["wildmatch_cxx"].libs = ["wildmatch-cxx"]
        self.cpp_info.components["wildmatch_cxx"].includedirs = ["include"]
        self.cpp_info.components["wildmatch_cxx"].requires = ["wildmatch_c"]
