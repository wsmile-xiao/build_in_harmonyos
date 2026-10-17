import os
import shlex
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv


class UtimerTest(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if can_run(self):
            binary = os.path.join(self.dependencies["utimer"].package_folder, "bin", "utimer")
            driver = os.path.join(self.source_folder, "test.py")
            self.run("python3 " + shlex.quote(driver) + " " + shlex.quote(binary), env="conanrun")
