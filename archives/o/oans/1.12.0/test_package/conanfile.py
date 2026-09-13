#!/usr/bin/env python3
from conan import ConanFile


class OansTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("OANS_BIN=oans ./test.sh", env="conanrun")
