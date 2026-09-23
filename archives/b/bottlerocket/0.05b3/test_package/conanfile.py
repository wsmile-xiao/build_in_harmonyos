from conan import ConanFile
from conan.tools.cmake import cmake_layout
from conan.tools.build import can_run
import os


class BottlerocketTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def test(self):
        if can_run(self):
            bindir = os.path.join(self.dependencies["bottlerocket"].package_folder, "bin")
            cmd_path = os.path.join(bindir, "br")
            assert os.path.isfile(cmd_path), f"br not found at {cmd_path}"
            self.run(f"{cmd_path} -h", env="conanrun")
