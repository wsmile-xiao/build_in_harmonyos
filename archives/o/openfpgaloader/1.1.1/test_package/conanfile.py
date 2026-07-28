import os

from conan import ConanFile
from conan.tools.build import can_run


class OpenfpgaloaderTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            binary = os.path.join(
                self.dependencies["openfpgaloader"].package_folder,
                "bin",
                "openFPGALoader",
            )
            script = os.path.join(self.source_folder, "test.sh")
            self.run(f'bash "{script}" "{binary}"', env="conanrun")
