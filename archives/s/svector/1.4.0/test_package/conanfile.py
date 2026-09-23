#!/usr/bin/env python3
"""Conan consumer test for svector — compiles test_svector.cpp against the
packaged header and runs the resulting assertions (test.sh)."""
import os

from conan import ConanFile


class SvectorTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # conanbuild env provides CXX/CXXFLAGS for compiling the consumer.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        dep = self.dependencies["svector"]
        incdir = os.path.join(dep.package_folder, dep.cpp_info.includedirs[0])
        self.run(f'{bash} test.sh "{incdir}"', env="conanbuild")
