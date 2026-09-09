from conan import ConanFile
from conan.tools.build import can_run
import os


class CcalTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            bindir = os.path.join(self.dependencies["ccal"].package_folder, "bin")
            cmd_path = os.path.join(bindir, "ccal")
            assert os.path.isfile(cmd_path), f"ccal not found at {cmd_path}"
            self.run(f"test -f {cmd_path}", env="conanrun")
