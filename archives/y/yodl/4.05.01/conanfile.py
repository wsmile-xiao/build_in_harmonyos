#!/usr/bin/env python3
"""Conan recipe for Yodl 4.05.01 built with CMake."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)


class YodlConan(ConanFile):
    name = "yodl"
    version = "4.05.01"
    description = "Pre-document language processor and conversion tools"
    license = "AGPL-3.0-only"
    homepage = "https://fbb-git.gitlab.io/yodl/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "CMakeLists.txt", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        project_dir = os.path.join(self.source_folder, "yodl")
        copy(self, "CMakeLists.txt", src=self.export_sources_folder,
             dst=project_dir)

    def generate(self):
        CMakeToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="yodl")
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README.txt", src=os.path.join(self.source_folder, "yodl"),
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        bindir = os.path.join(self.package_folder, "bin")
        includedir = os.path.join(self.package_folder, "share", "yodl")
        self.runenv_info.prepend_path("PATH", bindir)
        self.runenv_info.define_path("YODL_BIN", bindir)
        self.runenv_info.define_path("YODL_INCLUDE_PATH", includedir)
