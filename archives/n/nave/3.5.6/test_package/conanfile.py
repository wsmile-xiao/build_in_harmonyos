import os
from conan import ConanFile
from conan.tools.files import save, load


class NaveTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify nave.sh exists in the package bin directory
        nave_bin = os.path.join(self.dependencies["nave"].package_folder, "bin", "nave.sh")
        assert os.path.isfile(nave_bin), f"nave.sh not found at {nave_bin}"
        assert os.access(nave_bin, os.X_OK), f"nave.sh not executable at {nave_bin}"
        # Run nave --help to verify it works
        self.run("bash {} --help".format(nave_bin), env="conanrun")
