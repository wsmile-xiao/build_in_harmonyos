from conan import ConanFile
from conan.tools.build import can_run
import os


class Cd5TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            bindir = os.path.join(self.dependencies["cd5"].package_folder, "bin")
            cmd_path = os.path.join(bindir, "cd5")
            assert os.path.isfile(cmd_path), f"cd5 not found at {cmd_path}"
            self.run(f"test -f {cmd_path}", env="conanrun")
