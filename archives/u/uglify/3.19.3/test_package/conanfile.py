import os

from conan import ConanFile
from conan.tools.build import can_run


class UglifyTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            package_folder = self.dependencies["uglify"].package_folder
            executable = os.path.join(
                package_folder,
                "bin",
                "uglifyjs",
            ).replace("\\", "/")
            test_script = os.path.join(
                self.source_folder,
                "test.sh",
            ).replace("\\", "/")
            self.run(
                f'sh "{test_script}" "{executable}"',
                cwd=self.source_folder,
                env="conanrun",
            )
