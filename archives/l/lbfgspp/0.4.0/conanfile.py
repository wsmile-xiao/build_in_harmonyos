#!/usr/bin/env python3
"""Conan recipe — lbfgspp 0.4.0 (header-only C++ L-BFGS optimization library).

LBFGS++ is a header-only C++ library that implements the Limited-memory
BFGS algorithm (L-BFGS) for unconstrained minimization, and a modified
version of the L-BFGS-B algorithm for box-constrained problems.

Its only dependency is Eigen (also header-only).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class LbfgsppConan(ConanFile):
    name = "lbfgspp"
    version = "0.4.0"
    package_type = "header-library"

    description = "Header-only C++ library for L-BFGS and L-BFGS-B optimization"
    homepage = "https://lbfgspp.statr.me/"
    license = "MIT"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("eigen/3.4.0")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(self, "include/*", src=self.source_folder, dst=self.package_folder)
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "lbfgspp")
        self.cpp_info.set_property("cmake_target_name", "lbfgspp::lbfgspp")
        self.cpp_info.includedirs = ["include"]
