import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class HeirloomdoctoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # R34: test must genuinely depend on the package
        nroff = os.path.join(self.dependencies["heirloom-doctools"].package_folder, "bin", "nroff")
        # Run test.sh which verifies the nroff binary (ELF check + architecture check)
        self.run(f"sh {os.path.join(self.source_folder, 'test.sh')} {nroff}", env="conanrun")
