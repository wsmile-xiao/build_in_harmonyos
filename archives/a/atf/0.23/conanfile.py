#!/usr/bin/env python3
"""Conan recipe — atf 0.23 (Autotools).

ATF (Automated Testing Framework) provides C, C++ and shell test
frameworks for writing test programs.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AtfConan(ConanFile):
    name = "atf"
    version = "0.23"
    description = "Automated Testing Framework (ATF) - C/C++/shell test frameworks"
    license = "BSD-2-Clause"
    homepage = "https://github.com/freebsd/atf"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # L1: Run upstream official test suite (make check)
        # atf 的 make check 编译和链接 bootstrap 测试程序 (EXIT_CODE=0)
        # 实际测试执行需手动运行，详见 test_package/MANIFEST.yml
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # C core library
        self.cpp_info.components["atf-c"].libs = ["atf-c"]
        self.cpp_info.components["atf-c"].set_property("cmake_target_name", "atf::atf-c")

        # C++ wrapper library (depends on C core)
        self.cpp_info.components["atf-c++"].libs = ["atf-c++"]
        self.cpp_info.components["atf-c++"].requires = ["atf-c"]
        self.cpp_info.components["atf-c++"].set_property("cmake_target_name", "atf::atf-c++")
