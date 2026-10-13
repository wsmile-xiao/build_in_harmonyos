import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["utest"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_utest.py")
            compilers = self.conf.get("tools.build:compiler_executables", default={}) or {}
            cc = compilers.get("c")
            command = f'"{sys.executable}" "{test_script}" "{pkg}" --work-root "{self.build_folder}"'
            if cc:
                command += f' --compiler "{cc}"'
            self.run(command, env="conanrun")
