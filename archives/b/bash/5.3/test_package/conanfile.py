import os

from conan import ConanFile


class BashTestConan(ConanFile):
    """test_package for bash executable — runs test.sh which invokes bash --version."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("sh test.sh", env="conanrun")
