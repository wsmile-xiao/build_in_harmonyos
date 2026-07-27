import os

from conan import ConanFile
from conan.tools.build import can_run


class PicatTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["picat"]
            bin_dir = os.path.join(dep.package_folder, "bin")
            picat_cmd = os.path.join(bin_dir, "picat")
            lib_dir = os.path.join(dep.package_folder, "share", "picat", "lib")

            test_script = os.path.join(self.source_folder, "test_picat.pi")
            self.run(
                f'PICATPATH="{lib_dir}" "{picat_cmd}" "{test_script}"',
                env="conanrun"
            )
