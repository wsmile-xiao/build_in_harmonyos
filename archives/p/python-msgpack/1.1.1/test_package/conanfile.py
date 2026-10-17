#!/usr/bin/env python3
"""Conan test_package for python-msgpack 1.1.1 — consumer check (R34)."""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class PythonMsgpackTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["python-msgpack"].package_folder
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(pkg, "lib", py_ver, "site-packages")
        if not os.path.isfile(os.path.join(site, "msgpack", "__init__.py")):
            raise ConanException(f"msgpack missing under {site}")
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_python_msgpack.py")
        if not os.path.isfile(test_script):
            raise ConanException(
                f"test_python_msgpack.py missing: {test_script}")
        self.run(f"python3 '{test_script}' '{site}'", env="conanrun")
