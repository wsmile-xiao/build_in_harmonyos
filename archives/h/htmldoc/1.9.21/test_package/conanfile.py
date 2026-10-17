#!/usr/bin/env python3
"""Conan test_package for htmldoc 1.9.21 — consumer smoke test.

Runs test_htmldoc.py (real test source file, satisfies L0c) against the
installed htmldoc binary: --version assertion + real HTML→PDF conversion.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class HtmldocTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["htmldoc"].package_folder
        hbin = os.path.join(pkg, "bin", "htmldoc")
        test_script = os.path.join(os.path.dirname(__file__), "test_htmldoc.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_htmldoc.py missing: {test_script}")
        if not os.path.isfile(hbin):
            raise ConanException(f"htmldoc binary missing: {hbin}")
        # htmldoc links libpng dynamically (no static lib in ohpcd) → the
        # runtime needs LD_LIBRARY_PATH covering every dependency lib dir.
        lib_dirs = [
            os.path.join(d.package_folder, "lib")
            for d in self.dependencies.values()
            if os.path.isdir(os.path.join(d.package_folder, "lib"))
        ]
        ld_library_path = os.pathsep.join(lib_dirs)
        self.run(
            f'LD_LIBRARY_PATH="{ld_library_path}" '
            f'python3 "{test_script}" "{hbin}"'
        )
