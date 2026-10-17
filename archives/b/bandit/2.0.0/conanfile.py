#!/usr/bin/env python3
"""Conan recipe — bandit 2.0.0 (C++11 header-only BDD test framework).

bandit is a header-only C++11 BDD-style unit testing framework.
Nothing is compiled: the public header tree (bandit/ including the nested
snowhouse assertion framework submodule headers) is installed as-is.

Official GitHub archives do NOT bundle git submodules; the v2.0.0-locked
snowhouse submodule is therefore declared as a second official source and
extracted into bandit/assertion_frameworks/snowhouse before packaging.

R39 note: all source URLs are official GitHub archives (no mirrors/proxies).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class BanditConan(ConanFile):
    name = "bandit"
    version = "2.0.0"
    description = "bandit - a C++11 header-only BDD-style unit testing framework"
    license = "MIT"
    homepage = "https://github.com/banditcpp/bandit"
    url = "https://github.com/banditcpp/bandit"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # header-only C++11: no runtime/compile dependencies
        pass

    def layout(self):
        pass

    def source(self):
        # Multi-source: official bandit tarball + v2.0.0-locked snowhouse submodule
        for item in self.conan_data["sources"]:
            args = dict(item)
            args.setdefault("strip_root", True)
            get(self, **args)

    def build(self):
        # Apply the failure_formatter virtual-dtor adaptation patch
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*",
             src=os.path.join(self.source_folder, "bandit"),
             dst=os.path.join(self.package_folder, "include", "bandit"))
        copy(self, "LICENSE*",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # header-only: no libraries/binaries, just the public include tree
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "bandit")
        self.cpp_info.set_property("cmake_target_name", "bandit::bandit")