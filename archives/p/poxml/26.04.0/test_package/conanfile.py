#!/usr/bin/env python3
"""Consumer test for poxml/26.04.0.

The assertions live in test_poxml.py so the package ships a real test source
file (CI L0c requires one; conanfile.py alone does not count).
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class PoxmlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Runtime closure of the packaged tools.
        self.requires("qtbase/6.11.1")
        self.requires("kdoctools/6.19.0")
        self.requires("gettext/0.22.5.1")

    def test(self):
        if not can_run(self):
            return
        bindir = self.dependencies["poxml"].cpp_info.bindirs[0]
        test_script = os.path.join(self.source_folder, "test_poxml.py")
        self.run('"%s" "%s" "%s"' % (sys.executable, test_script, bindir),
                 env="conanrun")
