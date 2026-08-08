import os

from conan import ConanFile


class AcornTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_bin = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder, "bin"
        )
        self.run(f'PATH="{package_bin}:$PATH" sh test.sh', env="conanrun")
