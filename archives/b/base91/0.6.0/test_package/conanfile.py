import os

from conan import ConanFile
from conan.tools.build import cross_building


class Base91TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            return
        base91 = os.path.join(self.dependencies["base91"].package_folder, "bin", "base91")
        script = os.path.join(self.recipe_folder, "test_base91.sh")
        self.run(f'sh "{script}" "{base91}"', env="conanrun")
