import os
import sys

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(dep.package_folder, "bin")
        test_dir = self.source_folder
        if not os.path.exists(os.path.join(test_dir, "check_binaries.py")):
            test_dir = self.recipe_folder
        checker = os.path.join(test_dir, "check_binaries.py")
        self.run('"%s" "%s"' % (sys.executable, checker) + ' "%s"' % bindir,
                 env="conanrun")
