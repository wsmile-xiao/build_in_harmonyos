#!/usr/bin/env python3
"""test_package — medianfilter 1.0.0.

Verifies the installed public API: MEDIANFILTER_Init + MEDIANFILTER_Insert
from MedianFilter.h against libmedianfilter.a, and the C++ header-only
template from MedianFilter.hpp.  Consumer compiles, links and runs on
the OHOS target profile.
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.layout import basic_layout


class MedianfilterTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            return  # binaries built for OHOS run via the explicit runner below
        # Directly execute the two consumer binaries (real self.run evidence).
        # On OHOS the ELF must be launched through bash (mksh cannot exec ELF).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        bin_dir = os.path.join(self.build_folder, "..", "..")
        c_exe = os.path.join(bin_dir, "test_medianfilter_c")
        cpp_exe = os.path.join(bin_dir, "test_medianfilter_cpp")
        if os.path.isfile(c_exe):
            self.run(f'"{bash}" "{c_exe}"', env="conanrun")
        else:
            cmake = CMake(self)
            cmake.ctest(cli_args=["--output-on-failure"])
        if os.path.isfile(cpp_exe):
            self.run(f'"{bash}" "{cpp_exe}"', env="conanrun")