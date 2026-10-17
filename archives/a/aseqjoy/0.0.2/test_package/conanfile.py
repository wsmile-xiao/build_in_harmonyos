import os
from conan import ConanFile

class AseqjoyTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("sh test.sh", env="conanrun")
