import os

from conan import ConanFile
from conan.tools.build import can_run


class KimwituTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            script = os.path.join(self.source_folder, "test_kimwitu.sh")
            self.run(f"sh {script}", env="conanrun")
