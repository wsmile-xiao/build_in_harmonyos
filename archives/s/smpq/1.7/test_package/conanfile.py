#!/usr/bin/env python3
"""Consumer test for smpq/1.7.

smpq is a command line utility; the assertions live in test_smpq.py so the
package ships a real test source file (CI L0c requires one; conanfile.py
alone does not count).  The script drives the packaged binary through a real
MPQ create/info/list/extract round trip.
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class SmpqTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["smpq"]
        binary = os.path.join(dep.cpp_info.bindirs[0], "smpq")
        test_script = os.path.join(self.source_folder, "test_smpq.py")
        self.run('"%s" "%s" "%s"' % (sys.executable, test_script, binary),
                 env="conanrun")
