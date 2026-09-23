from conan import ConanFile
from conan.tools.build import can_run
import os


class CalifeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            bindir = os.path.join(self.dependencies["calife"].package_folder, "bin")
            cmd_path = os.path.join(bindir, "calife")
            assert os.path.isfile(cmd_path), f"calife not found at {cmd_path}"
            self.run(f"test -f {cmd_path}", env="conanrun")
