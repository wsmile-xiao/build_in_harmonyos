from conan import ConanFile
from conan.tools.build import can_run
import os


class CalTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            bindir = os.path.join(self.dependencies["cal"].package_folder, "bin")
            cmd_path = os.path.join(bindir, "cal")
            assert os.path.isfile(cmd_path), f"cal not found at {cmd_path}"
            self.run(f"test -f {cmd_path}", env="conanrun")
