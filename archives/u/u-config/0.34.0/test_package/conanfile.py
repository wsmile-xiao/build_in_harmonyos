#!/usr/bin/env python3
"""test_package for u-config 0.34.0 — consumer verification of the installed
pkg-config tool (the tool package ships no library to link against)."""
from conan import ConanFile


class UConfigTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("sh test.sh", env="conanrun")
