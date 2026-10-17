import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class RpgTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        executable = os.path.join(package_folder, "bin", "rpg")
        if not os.path.isfile(executable):
            raise ConanException("missing packaged command: bin/rpg")

        if can_run(self):
            script = os.path.join(self.recipe_folder, "test_rpg.py")
            self.run(f'"{sys.executable}" "{script}"', env="conanrun")
