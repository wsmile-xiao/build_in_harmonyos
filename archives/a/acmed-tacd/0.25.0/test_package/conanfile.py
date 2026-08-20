import os

from conan import ConanFile
from conan.tools.build import can_run


class AcmedTacdTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        executable = os.path.join(package_folder, "bin", "tacd")
        assert os.path.isfile(executable), f"tacd binary not found: {executable}"

        if can_run(self):
            script = os.path.join(self.recipe_folder, "test.sh")
            self.run(f'bash "{script}" "{executable}"', env="conanrun")
        else:
            with open(executable, "rb") as binary:
                assert binary.read(4) == b"\x7fELF", "tacd is not an ELF binary"
