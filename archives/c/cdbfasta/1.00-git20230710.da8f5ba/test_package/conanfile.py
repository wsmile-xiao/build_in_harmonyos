import os
import sys

from conan import ConanFile
from conan.tools.cmake import cmake_layout


class CdbfastaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(dep.package_folder, "bin")
        cdbfasta = os.path.join(bindir, "cdbfasta")
        cdbyank = os.path.join(bindir, "cdbyank")
        script = os.path.join(self.recipe_folder, "test_cdbfasta.py")

        self.run(
            f'"{sys.executable}" "{script}" "{cdbfasta}" "{cdbyank}"',
            env="conanrun",
        )
