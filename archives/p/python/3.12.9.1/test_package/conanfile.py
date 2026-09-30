#!/usr/bin/env python3
"""Conan test_package for Python 3.12.9.

E212: Uses sys.executable (conan-provided Python) to run test_python.py,
avoiding HMDFS dlopen limitations that affect the built python3.12 directly.

E131: Unsets LD environment variable before executing the built Python binary
to avoid dynamic linker override issues on OHOS.

R34: The test exercises the built python3.12 binary — version check and
key C extension module imports (ssl, hashlib, sqlite3, zlib, bz2, lzma, ctypes).
"""
import os
import sys

from conan import ConanFile


class PythonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        executable = os.path.join(dep.package_folder, "bin", "python3.12")
        script = os.path.join(self.recipe_folder, "test_python.py")

        # E212: Use conan-provided Python (sys.executable) to run the test
        # script, which in turn uses subprocess to invoke the built python3.12.
        # Do NOT use env="conanrun" — it sets LD_LIBRARY_PATH to the package's
        # lib/ dir, causing the system python3 to load the built libpython3.12.so
        # instead of its own (symbol mismatch crash).
        # test_python.py sets up the correct env for the subprocess instead.
        self.run(
            f'"{sys.executable}" "{script}" "{executable}" "{dep.package_folder}"',
        )
