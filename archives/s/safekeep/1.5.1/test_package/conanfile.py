import os
import sys

from conan import ConanFile


class SafekeepTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        if str(self.settings.os) == "OHOS":
            self.requires("rdiff-backup/2.2.6")

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        package_folder = dep.package_folder
        script = os.path.join(self.recipe_folder, "test_safekeep_package.py")
        args = [f'"{sys.executable}"', f'"{script}"', f'"{package_folder}"']
        if str(self.settings.os) == "OHOS":
            rdiff_dep = self.dependencies["rdiff-backup"]
            args.extend(["--rdiff-backup-package", f'"{rdiff_dep.package_folder}"'])
        self.run(" ".join(args), env="conanrun")
