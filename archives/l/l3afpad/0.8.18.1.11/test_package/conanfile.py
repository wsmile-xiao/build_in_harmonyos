#!/usr/bin/env python3
"""Consumer test for l3afpad/0.8.18.1.11.

l3afpad is a GTK+3 GUI text editor (see test_l3afpad.py for why a headless run
can only assert up to GTK display initialisation).  The assertions live in
test_l3afpad.py so the package ships a real test source file (CI L0c requires
one; conanfile.py alone does not count).
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class L3afpadTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["l3afpad"]
        binary = os.path.join(dep.cpp_info.bindirs[0], "l3afpad")
        test_script = os.path.join(self.source_folder, "test_l3afpad.py")
        # env="conanrun" puts the dependency libdirs on LD_LIBRARY_PATH, which
        # the GTK+3 closure needs; the child python inherits it.
        self.run('"%s" "%s" "%s"' % (sys.executable, test_script, binary),
                 env="conanrun")
