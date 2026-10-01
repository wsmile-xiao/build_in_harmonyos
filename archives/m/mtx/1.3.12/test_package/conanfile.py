#!/usr/bin/env python3
"""Conan test package for the mtx media changer CLI tools.

MTX has no library API: every product of this recipe is a command line
tool, so the consumer test executes the packaged binaries instead of
linking a helper against them.  ``test.sh`` performs the actual probes
and is also runnable by hand on a device:

    bash test_package/test.sh <package_folder>
"""

import os
import shutil

from conan import ConanFile

TOOLS = ("mtx", "tapeinfo", "loaderinfo", "scsitape", "scsieject")


class MtxTestConan(ConanFile):
    name = "mtx-test"
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["mtx"].package_folder
        bindir = os.path.join(package_folder, "bin")
        for tool in TOOLS:
            tool_path = os.path.join(bindir, tool)
            if not os.path.isfile(tool_path):
                raise AssertionError(f"packaged tool is missing: {tool_path}")

        shell = shutil.which("bash") or "/bin/sh"
        self.run(f'"{shell}" test.sh "{package_folder}"', env="conanrun")
