import os
from conan import ConanFile


class AutoconfArchiveTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["autoconf-archive"]
        aclocal_dir = os.path.join(dep.package_folder, "share", "aclocal")
        self.run(f"sh {os.path.join(self.source_folder, 'test_macros.sh')} {aclocal_dir}")
