import os
from conan import ConanFile


class ColordiffTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["colordiff"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        # R34: exercise the packaged artifact — verify colordiff and cdiff
        # scripts are present, executable, have correct shebang, and that
        # colordiff --version runs successfully.
        self.run(f"bash test_colordiff.sh {bin_dir}", env="conanrun")
        self.output.info("colordiff: OK")
