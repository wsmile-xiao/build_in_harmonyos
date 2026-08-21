import os
import sys

from conan import ConanFile


class TypobusterTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.recipe_folder, "test_typobuster.py")
        self.run(f'"{sys.executable}" "{script}"', env="conanrun")
