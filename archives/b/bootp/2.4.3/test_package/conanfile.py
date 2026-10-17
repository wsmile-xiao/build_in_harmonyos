from conan import ConanFile
from conan.tools.build import can_run
import os


class BootpTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            bindir = os.path.join(self.dependencies["bootp"].package_folder, "bin")
            for cmd in ["bootpd", "bootpef", "bootpgw"]:
                cmd_path = os.path.join(bindir, cmd)
                assert os.path.isfile(cmd_path), f"{cmd} not found at {cmd_path}"
                self.run(f"test -f {cmd_path}", env="conanrun")
