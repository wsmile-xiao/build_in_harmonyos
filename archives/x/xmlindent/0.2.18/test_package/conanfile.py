#!/usr/bin/env python3
"""Conan test_package — xmlindent 0.2.18 consumer verification.

Exercises the packaged CLI from a consumer's point of view (stdin filter, file
arguments, -o/-i/-t/-w, version/help, error handling).

This is CONSUMER verification only.  The single upstream regression fixture
shipped by 0.2.18 is executed by the recipe's build() step
(`run_upstream_tests.sh`) and is NOT counted here.
"""
import os
import shutil

from conan import ConanFile


class XmlindentTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = (os.environ.get("CONFIG_SHELL") or shutil.which("bash")
                or "/data/service/hnp/bin/bash")
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        script = os.path.join(self.source_folder, "test_xmlindent.sh")
        self.run(f'{bash} {script} "{os.path.join(pkg_folder, "bin")}"',
                 env="conanrun")
