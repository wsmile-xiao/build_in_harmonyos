import os
import shutil

from conan import ConanFile


class DiasporaInstallerTestConan(ConanFile):
    """test_package for diaspora-installer — shell syntax + version smoke test."""

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["diaspora-installer"]
        share_dir = os.path.join(dep.package_folder, "share", "diaspora-installer")
        script = os.path.join(self.recipe_folder, "test.sh")
        # Prefer a POSIX shell; CONFIG_SHELL is set by the CI worker
        # (e.g. /data/service/hnp/bin/bash), otherwise fall back to `sh`.
        shell = os.environ.get("CONFIG_SHELL") or shutil.which("sh") or "sh"
        self.run(f'{shell} "{script}" "{share_dir}"')