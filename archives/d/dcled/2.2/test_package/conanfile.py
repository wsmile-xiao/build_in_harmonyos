#!/usr/bin/env python3
"""Consumer test for dcled 2.2 (test_type = "explicit").

The assertions live in test_dcled.py: they execute the *installed* binaries and
check what they actually print. The call below only drives the Python
interpreter — on this platform the conan runner crashes with SIGSEGV when it
spawns the target binary itself, so spawning is delegated to the script, which
uses subprocess with an explicitly assembled LD_LIBRARY_PATH.
"""

import os
import sys

from conan import ConanFile
from conan.tools.layout import basic_layout


class DcledTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _dependency_libdirs(self):
        """libdirs of every dependency in the graph (libusb, in practice)."""
        dirs = []
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                dirs.append(os.path.join(dep.package_folder, str(libdir)))
        return dirs

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        script = os.path.join(self.recipe_folder, "test_dcled.py")
        parts = [
            f'"{sys.executable}"',
            f'"{script}"',
            f'"{os.path.join(dep.package_folder, "bin", "dcled")}"',
            f'"{os.path.join(dep.package_folder, "bin", "cpuload")}"',
            f'"{os.path.join(dep.package_folder, "share", "dcled")}"',
        ]
        parts.extend(f'"{libdir}"' for libdir in self._dependency_libdirs())
        self.run(" ".join(parts), env="conanrun")
