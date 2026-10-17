#!/usr/bin/env python3
"""Conan test_package for pybeam 0.8.1 — import + real API test."""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class PybeamTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            python_exe = sys.executable
            py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
            # pybeam 与其运行期依赖 construct 都要在 PYTHONPATH 上
            sites = []
            for dep in ("pybeam", "construct"):
                pkg = self.dependencies[dep].package_folder
                sites.append(os.path.join(pkg, "lib", py_ver, "site-packages"))
            test_script = os.path.join(os.path.dirname(__file__), "test_pybeam.py")
            self.run(f'PYTHONPATH="{os.pathsep.join(sites)}" '
                     f'{python_exe} "{test_script}"', env="conanrun")
