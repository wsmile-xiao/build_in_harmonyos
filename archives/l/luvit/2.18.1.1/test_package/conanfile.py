#!/usr/bin/env python3
"""Conan test_package for luvit 2.18.1.1."""
import os
import shlex
import shutil
import sys

from conan import ConanFile


class LuvitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        root = next(iter(self.dependencies.values())).package_folder
        resource_probe = os.path.join(self.source_folder, "check_luvit_resources.py")
        self.run(" ".join(shlex.quote(arg) for arg in (sys.executable, resource_probe, root)))
        luvi = shutil.which("luvi")
        if not luvi:
            self.output.warning("luvit upstream tests are packaged but the external luvi runtime is not available in PATH; full inventory integrity was verified instead")
            return
        luvit_root = os.path.join(root, "share", "luvit")
        self.run("{} {} -- tests/run.lua".format(luvi, luvit_root))
