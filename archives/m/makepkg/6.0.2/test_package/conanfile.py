import os
import shutil

from conan import ConanFile


class MakepkgTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["makepkg"]
        makepkg = os.path.join(dep.package_folder, "bin", "makepkg")
        config = os.path.join(dep.package_folder, "etc", "makepkg.conf")
        test_script = os.path.join(self.source_folder, "test.sh")
        bash = os.environ.get("CONAN_BASH") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        self.run(
            f'MAKEPKG_BIN="{makepkg}" MAKEPKG_CONF="{config}" "{bash}" "{test_script}"',
            env="conanrun",
        )
