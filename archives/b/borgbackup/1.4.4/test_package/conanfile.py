import os

from conan import ConanFile
from conan.tools.files import save


class BorgbackupTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        pkg = self.dependencies["borgbackup"]
        site_packages = os.path.join(pkg.package_folder, "lib", "site-packages")
        save(self, "pkg_path.txt", site_packages)

    def test(self):
        self.run("python3 test_borg.py")
