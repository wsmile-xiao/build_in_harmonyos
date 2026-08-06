#!/usr/bin/env python3
import os
from conan import ConanFile

class MupdfToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    def requirements(self):
        self.requires(self.tested_reference_str)
    def build(self):
        pass
    def test(self):
        self.run("mutool -v", env="conanrun")
