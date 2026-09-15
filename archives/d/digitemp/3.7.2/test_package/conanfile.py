from conan import ConanFile
import os
import shlex
import sys


class DigitempTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.recipe_folder, "test_digitemp.py")
        self.run(
            f"{shlex.quote(sys.executable)} {shlex.quote(script)} {shlex.quote(package)}",
            env="conanrun",
        )
