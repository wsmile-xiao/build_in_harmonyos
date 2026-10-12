from conan import ConanFile
from conan.tools.layout import basic_layout
import os
import sys


class SixerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package = self.dependencies["sixer"]
        script = os.path.join(self.source_folder, "test_sixer.py")
        self.run(
            f'"{sys.executable}" "{script}" "{package.package_folder}"',
            cwd=self.source_folder,
            env="conanrun",
        )
