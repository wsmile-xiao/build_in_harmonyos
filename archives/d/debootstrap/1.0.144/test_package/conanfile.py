import os
import shutil

from conan import ConanFile


class DebootstrapTestConan(ConanFile):
    """test_package for debootstrap — runs the real `debootstrap --version`."""

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["debootstrap"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        share_dir = os.path.join(dep.package_folder, "share", "debootstrap")
        shell = os.environ.get("CONFIG_SHELL") or shutil.which("sh") or "sh"
        # 1) assertion suite against the real packaged artifact.
        self.run(f'"{shell}" "{os.path.join(self.recipe_folder, "test.sh")}" "{bin_dir}" "{share_dir}"')
        # 2) rule12: genuine consumer end-to-end case — real debootstrap
        #    --download-only run against a locally built file:// Debian mirror.
        self.run(f'"{shell}" "{os.path.join(self.recipe_folder, "consumer_e2e.sh")}" "{bin_dir}" "{share_dir}"')