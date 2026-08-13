#!/usr/bin/env python3
"""test_package for owamp 3.4-10.

Consumer-level test (R34): verifies the installed owamp CLI tools are
present in the package and that the shipped binaries actually run on the
target platform.  The test source is test_owamp.sh (L0c): it checks the
7 installed tools and runs the upstream test entry owtvec (exit 0 =
OWAMP spec Appendix B exponential-deviate self-check).
"""
import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["owamp"]
        # run the test source script against the package prefix
        script = os.path.join(self.source_folder, "test_owamp.sh")
        self.run(f"{script} {dep.package_folder}", env="conanrun")
