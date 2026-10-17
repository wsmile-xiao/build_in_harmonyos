import os

from conan import ConanFile
from conan.tools.build import can_run


class MawkTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            package = self.dependencies["mawk"].package_folder
            self.run(f'sh test.sh "{os.path.join(package, "bin", "mawk")}"')
