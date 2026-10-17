#!/usr/bin/env python3
"""Consumer test for tornado/6.5.2.

tornado is installed as a wheel into the package's site-packages, which
package_info() exports on PYTHONPATH (runenv).  The assertions themselves live
in test_tornado.py so the package ships a real test source file (CI L0c
requires one; conanfile.py alone does not count).
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TornadoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        test_script = os.path.join(self.source_folder, "test_tornado.py")
        self.run('"%s" "%s"' % (sys.executable, test_script), env="conanrun")
