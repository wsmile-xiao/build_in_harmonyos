import os
from conan import ConanFile
from conan.tools.build import can_run

class Ksh93TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        ksh_path = os.path.join(pkg_folder, "bin", "ksh")

        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'sh "{test_script}" "{ksh_path}"')
