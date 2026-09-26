#!/usr/bin/env python3
"""yaskkserv consumer test: the packaged server must run and self-report."""
from conan import ConanFile
from conan.tools.env import VirtualRunEnv


class YaskkservTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        self.run("sh ./test.sh", env="conanrun")
