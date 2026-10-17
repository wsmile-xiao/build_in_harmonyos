from conan import ConanFile
from conan.tools.build import can_run
import os


class BwbarTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            bindir = os.path.join(self.dependencies["bwbar"].package_folder, "bin")
            cmd_path = os.path.join(bindir, "bwbar")
            assert os.path.isfile(cmd_path), f"bwbar not found at {cmd_path}"
            self.run(f"{cmd_path} --help", env="conanrun")
