#!/usr/bin/env python3
"""test_package for mklibs 0.1.46 — consumer verification.

Exercises the installed command line tools the way a user would: the C++
ELF reader is run against real ELF objects (its own binary), and the two
Python entry points are invoked through the interpreter.  The upstream
source tree ships no automated test suite (no tests/ directory, no
`check` target, no debian/tests), so this consumer test is the executable
verification shipped with the package; the upstream entry-point survey
lives in reports/test-report.md.
"""
import os
import shutil

from conan import ConanFile


class MklibsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = (os.environ.get("CONFIG_SHELL")
                or shutil.which("bash")
                or "/bin/sh")
        self.run(f"{bash} test.sh", cwd=self.source_folder, env="conanrun")
