#!/usr/bin/env python3
"""Conan test_package for megahit 1.2.9 (consumer-perspective verification).

The functional test logic lives in test_megahit.py, kept as a real test
source file inside test_package/ (CI build_and_test.sh L0c requires test
source files: c/cpp/cc/cxx/sh/py, conanfile.py excluded). This conanfile
only drives the script; a non-zero exit or failed assertion fails `conan test`.
"""
import os

from conan import ConanFile


class MegahitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = self.dependencies[self.tested_reference_str].cpp_info.bindirs[0]
        workdir = os.path.join(self.build_folder, "run")
        script = os.path.join(os.path.dirname(__file__), "test_megahit.py")
        # conanrun env: package bindirs on PATH and shared lib dirs in
        # LD_LIBRARY_PATH; every subprocess inside the script inherits it.
        self.run('python3 "{}" "{}" "{}"'.format(script, bindir, workdir),
                 env="conanrun")
