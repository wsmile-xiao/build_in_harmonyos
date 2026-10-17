#!/usr/bin/env python3
"""Consumer test for the packaged wsdd CLI."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class WsddTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["wsdd"]
        bindir = dep.cpp_info.bindirs[0]
        if not os.path.isabs(bindir):
            bindir = os.path.join(dep.package_folder, bindir)
        binary = os.path.join(bindir, "wsdd")
        script = os.path.join(self.source_folder, "test_wsdd.py")
        self.run(f'"{sys.executable}" "{script}" "{binary}"', env="conanrun")
