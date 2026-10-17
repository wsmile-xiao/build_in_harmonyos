import os
import shlex

from conan import ConanFile


class BoulderGameTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["boulder-game"].package_folder
        script = os.path.join(self.source_folder, "test.sh")
        self.run("bash " + shlex.quote(script) + " " + shlex.quote(package), env="conanrun")
