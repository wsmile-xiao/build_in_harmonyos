import os
from conan import ConanFile
from conan.tools.build import can_run

class ZsignTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            self.run("zsign --help", run_environment=True)
