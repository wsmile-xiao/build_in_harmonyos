#!/usr/bin/env python3
"""Conan test_package — leaps 0.9.1 consumer run of the installed tool.

R34/L0c: the test actually EXECUTES the packaged `leaps` binary via the
test source file test_leaps.sh and asserts its usage banner (caddy /
libjxl-tools precedent).
"""

import os

from conan import ConanFile


class LeapsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        leaps = None
        for dependency in self.dependencies.host.values():
            if dependency.ref.name == "leaps":
                bindirs = dependency.cpp_info.bindirs or ["bin"]
                bindir = bindirs[0]
                if not os.path.isabs(bindir):
                    bindir = os.path.join(dependency.package_folder, bindir)
                leaps = os.path.join(bindir, "leaps")
        if not leaps or not os.path.isfile(leaps):
            raise Exception("leaps binary not found in package bindirs")

        # L0c: run the actual test source file (test_leaps.sh) — the CI
        # gate requires a test source in test_package/ besides conanfile.py.
        test_script = os.path.join(self.recipe_folder, "test_leaps.sh")
        self.run('sh "%s" "%s"' % (test_script, leaps))
        self.output.info("leaps tool consumer test PASSED")
