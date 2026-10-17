#!/usr/bin/env python3
"""Conan recipe — cxxtest 4.1

CxxTest is a lightweight, header-only C++ unit testing framework (LGPL-2.1).
The package ships no compiled library: the cxxtest/ headers are included
directly by test code, and the cxxtestgen test-driver generator is a Python
program that only runs at build time (the target machine does not need a
Python runtime). The recipe installs the header set to include/ and the
Python 3 driver package (python/python3/cxxtest/ + bin/cxxtestgen) to res/,
exposed via user_info.cxxtestgen so consumers can generate runners with a
plain "python3 <path> <args>" call.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CxxTestConan(ConanFile):
    name = "cxxtest"
    version = "4.1"
    description = "A lightweight, header-only C++ unit testing framework with a Python-driven test generator"
    license = "LGPL-2.1"
    homepage = "https://github.com/CxxTest/cxxtest"
    url = "https://github.com/CxxTest/cxxtest"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only: nothing to compile; keep the patch-apply call for G1
        apply_conandata_patches(self)

    def package(self):
        # 1) The header set — the actual "library" (no compiled artefacts).
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "cxxtest"),
             dst=os.path.join(self.package_folder, "include", "cxxtest"))
        copy(self, "*.cpp",
             src=os.path.join(self.source_folder, "cxxtest"),
             dst=os.path.join(self.package_folder, "include", "cxxtest"))
        # Root.cpp is included directly by generated runners (source snippet,
        # not a compilation unit of a prebuilt library).
        # 2) The build-time Python driver (Python 3 line; Py2 line dropped).
        copy(self, "*.py",
             src=os.path.join(self.source_folder, "python", "python3", "cxxtest"),
             dst=os.path.join(self.package_folder, "res", "cxxtest"))
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        # header-only: no build dependency on os/compiler/build_type
        self.info.clear()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "CxxTest")
        self.cpp_info.set_property("cmake_target_name", "CxxTest::CxxTest")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # Location of the cxxtestgen driver for consumers (build-time tool):
        # python3 <res_folder>/cxxtest/cxxtestgen.py --error-printer -o runner.cpp suite.h
        res_dir = os.path.join(self.package_folder, "res")
        self.cpp_info.resdirs = ["res"]
        self.cpp_info.set_property("cxxtest_driver", os.path.join(res_dir, "cxxtest", "cxxtestgen.py"))
