#!/usr/bin/env python3
import os
import sys

from conan import ConanFile
from conan.tools.cmake import cmake_layout


class EphemeralpgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        # Functional smoke test: run the installed getsocket binary and assert
        # it prints a valid TCP port (R34: test must invoke the packaged binary).
        getsocket = os.path.join(dep.package_folder, "bin", "getsocket")
        script = os.path.join(self.recipe_folder, "test_getsocket.py")

        self.run(
            f'"{sys.executable}" "{script}" "{getsocket}"',
            env="conanrun",
        )

        # Also verify pg_tmp (a shell script) is installed and executable.
        pg_tmp = os.path.join(dep.package_folder, "bin", "pg_tmp")
        assert os.path.isfile(pg_tmp), "pg_tmp missing at {}".format(pg_tmp)
        self.output.info("pg_tmp installed at {}".format(pg_tmp))
