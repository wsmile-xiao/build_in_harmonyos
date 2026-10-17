#!/usr/bin/env python3
import os
from conan import ConanFile


class UnitsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{shell} test.sh", env="conanrun")
