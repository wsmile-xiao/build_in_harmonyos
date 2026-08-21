#!/usr/bin/env python3
"""test_package for ngspice — runs test.sh which invokes ngspice --version."""
from conan import ConanFile


class NgspiceTestConan(ConanFile):
    """test_package for ngspice executable — runs ngspice --version."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: test must actually exercise the packaged binary
        self.run("sh test.sh", env="conanrun")
