import os

from conan import ConanFile
from conan.tools.build import can_run


class LightGBMTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["lightgbm"]
        candidates = [
            os.path.join(dep.package_folder, "bin", "lightgbm"),
            os.path.join(dep.package_folder, "bin", "lightgbm.exe"),
        ]
        if can_run(self):
            for candidate in candidates:
                if os.path.exists(candidate):
                    self.run(f'"{candidate}" --help || test $? -eq 255', env="conanrun")
                    break
