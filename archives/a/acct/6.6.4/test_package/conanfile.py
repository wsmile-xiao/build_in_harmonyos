import os

from conan import ConanFile


class AcctTestConan(ConanFile):
    """test_package for acct executables — runs test.sh which invokes ac --version."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("ac --version", env="conanrun")
