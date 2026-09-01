import os
from conan import ConanFile


class AurpublishTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["aurpublish"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        # R34: exercise the packaged script for real — `--help` (exit 0,
        # usage text) plus `setup` hook installation inside a scratch git
        # repository (validates the runtime HOOKSDIR resolution against the
        # installed package layout).
        self.run(f"bash test_aurpublish.sh {bin_dir}", env="conanrun")
        self.output.info("aurpublish: OK")
