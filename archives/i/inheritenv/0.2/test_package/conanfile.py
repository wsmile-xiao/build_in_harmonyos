#!/usr/bin/env python3
"""test_package for inheritenv — verifies inheritenv.el installation and,
when emacs is available on the host, runs the upstream ERT suite verbatim."""
import os

from conan import ConanFile


class InheritenvTestConan(ConanFile):
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["inheritenv"]
        probe = os.path.join(self.source_folder, "test_inheritenv.py")
        self.run(f"python3 \"{probe}\" \"{dep.package_folder}\"",
                 env="conanrun")
