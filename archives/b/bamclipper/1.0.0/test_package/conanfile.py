import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.layout import basic_layout


class BamclipperTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("bash/5.3")

    def layout(self):
        basic_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if can_run(self):
            bamclipper = os.path.join(
                self.dependencies["bamclipper"].package_folder, "bin", "bamclipper.sh"
            )
            bash = os.path.join(
                self.dependencies["bash"].package_folder, "bin", "bash"
            )
            samtools = os.path.join(
                self.dependencies["samtools"].package_folder, "bin", "samtools"
            )
            parallel = os.path.join(
                self.dependencies["parallel"].package_folder, "bin", "parallel"
            )
            perl = os.path.join(
                self.dependencies["perl"].package_folder, "bin", "perl"
            )
            script = os.path.join(self.source_folder, "test.sh")
            self.run(
                f'"{bash}" "{script}" "{bamclipper}" "{samtools}" '
                f'"{parallel}" "{perl}" "{bash}"',
                env="conanrun",
            )
