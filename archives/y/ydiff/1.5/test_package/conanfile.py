import os

from conan import ConanFile
from conan.tools.build import can_run


class YdiffTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        executable = os.path.join(
            self.dependencies["ydiff"].package_folder,
            "bin",
            "ydiff",
        )
        test_script = os.path.join(self.source_folder, "test_ydiff.py")
        self.run(
            f'python3 "{test_script}" "{executable}"',
            env="conanrun",
        )
