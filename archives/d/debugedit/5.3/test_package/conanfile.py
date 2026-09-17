#!/usr/bin/env python3
"""Conan test_package for debugedit 5.3.

Verifies installed CLI tools exist and debugedit runs --version /
-i (add build-id to an ELF file).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building


class DebugeditTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["debugedit"].package_folder
        bindir = os.path.join(pkg, "bin")
        tools = ["debugedit", "debugedit-classify-ar", "sepdebugcrcfix"]
        missing = [t for t in tools if not os.path.isfile(os.path.join(bindir, t))]
        if missing:
            raise SystemExit(f"FAIL: missing CLI tools: {missing}")
        self.output.info(f"OK: {len(tools)} CLI tools present in {bindir}")
        script = os.path.join(self.source_folder, "test_debugedit.sh")
        if cross_building(self):
            self.output.info("cross-building: only verifying test script + tools present")
            if not os.path.isfile(script):
                raise SystemExit("FAIL: test_debugedit.sh missing")
            return
        self.run(f"sh {script} {bindir}", env="conanrun")
