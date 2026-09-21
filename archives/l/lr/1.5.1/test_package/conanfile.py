#!/usr/bin/env python3
"""test_package for lr — exercises the packaged lr binary (R34).

Upstream lr 1.5.1 ships no test suite at all (its Makefile only has the all/
clean/install/FRC targets), so test_lr.sh is the adaptation regression suite: it runs the
*installed* binary against a generated fixture tree and asserts on real output
and on documented exit statuses.  It fails when bin/lr is missing or broken,
which is what CI L1e checks by sabotaging the package's bin/.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class LrTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["lr"]
        package_folder = dep.package_folder
        if not os.path.isfile(os.path.join(package_folder, "bin", "lr")):
            raise ConanException("test_package: packaged bin/lr is missing")
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        self.run(
            "LR_PACKAGE_FOLDER={0} {1} test_lr.sh".format(
                '"{0}"'.format(package_folder), shell
            ),
            env="conanrun",
        )
