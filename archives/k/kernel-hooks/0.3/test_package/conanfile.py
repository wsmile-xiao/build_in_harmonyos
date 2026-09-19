import os
from conan import ConanFile


class KernelHooksTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["kernel-hooks"].package_folder
        script = os.path.join(self.source_folder, "test_package.sh")
        self.run(f'sh "{script}" "{pkg_folder}"')
