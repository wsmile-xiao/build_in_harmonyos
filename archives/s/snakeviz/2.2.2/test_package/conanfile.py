#!/usr/bin/env python3
"""Consumer test for snakeviz/2.2.2.

snakeviz is a pure-Python wheel application; the assertions live in
test_snakeviz.py so the package ships a real test source file (CI L0c
requires one; conanfile.py alone does not count).

The run environment provides PYTHONPATH for both snakeviz and its tornado
dependency (each wheel package prepends its own site-packages), so the test
script can simply ``import snakeviz``.
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class SnakevizTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # tornado is only transitive via snakeviz; declare it explicitly so
        # its runenv (PYTHONPATH) is part of this test's environment.
        self.requires("tornado/6.5.2")

    def test(self):
        if not can_run(self):
            return
        test_script = os.path.join(self.source_folder, "test_snakeviz.py")
        self.run('"%s" "%s"' % (sys.executable, test_script), env="conanrun")
