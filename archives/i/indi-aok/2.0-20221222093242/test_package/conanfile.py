import os
import sys

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        driver = os.path.join(dep.cpp_info.bindirs[0], "indi_lx200aok")
        xml = os.path.join(dep.cpp_info.resdirs[0], "indi", "indi_aok.xml")
        # the INDI core libraries the driver links against live in libindi's package
        indi = self.dependencies["libindi"]
        indi_libdir = os.path.join(indi.package_folder, indi.cpp_info.libdirs[0])

        test_dir = self.source_folder
        if not os.path.exists(os.path.join(test_dir, "check_driver.py")):
            test_dir = self.recipe_folder
        checker = os.path.join(test_dir, "check_driver.py")

        argv = [sys.executable, checker, driver, dep.cpp_info.bindirs[0], xml, indi_libdir]
        self.run(" ".join('"%s"' % item for item in argv), env="conanrun")
