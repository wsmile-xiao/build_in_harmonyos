import os
import shutil

from conan import ConanFile


class RemindTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["remind"].package_folder
        script = os.path.join(self.source_folder, "test_remind.sh")
        shell = shutil.which("sh") or "/system/bin/sh"
        self.run("{} {} {}".format(shell, script, package_folder), env="conanrun")
