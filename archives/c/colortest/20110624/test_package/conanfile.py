import os

from conan import ConanFile


class ColortestTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["colortest"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        # R34: exercise the packaged artifacts with real smoke tests
        # (script presence, executable bit, shebang, perl/bash syntax and
        # actual color-table output).
        self.run(f'sh test_colortest.sh "{bin_dir}"', env="conanrun")
        self.output.info("colortest: OK")
