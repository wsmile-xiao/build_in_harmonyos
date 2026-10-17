import os
import shlex
import sys

from conan import ConanFile


class BisonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["bison"].package_folder
        bison = os.path.join(package_folder, "usr", "bin", "bison")
        pkgdata = os.path.join(package_folder, "usr", "share", "bison")
        script = os.path.join(self.source_folder, "test_bison.py")
        clang = "/data/service/hnp/bin/clang"
        command = "BISON_PKGDATADIR={} {}".format(
            shlex.quote(pkgdata),
            " ".join(shlex.quote(value) for value in
                     (sys.executable, script, bison, clang)),
        )
        self.run(command)
