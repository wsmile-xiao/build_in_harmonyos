#!/usr/bin/env python3
"""Consumer test for the packaged WAILI programs."""

import json
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class WailiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "test_waili.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["waili"]
        bindir = dep.cpp_info.bindirs[0]
        if not os.path.isabs(bindir):
            bindir = os.path.join(dep.package_folder, bindir)
        script = os.path.join(self.source_folder, "test_waili.py")
        self.run(f'"{sys.executable}" "{script}" "{bindir}"', env="conanrun")
