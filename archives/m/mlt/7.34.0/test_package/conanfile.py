#!/usr/bin/env python3
"""Conan test_package for mlt 7.34.0 — consumer check.

Runs test_mlt.py (real test source file, satisfies L0c) against the
installed libmlt: loads the shared library and verifies mlt_version().
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class MltTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["mlt"].package_folder
        lib_dir = os.path.join(pkg, "lib")
        test_script = os.path.join(os.path.dirname(__file__), "test_mlt.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_mlt.py missing: {test_script}")
        # libmlt links ffmpeg/libxml2 dynamically — expose their lib dirs
        deps = []
        for d in self.dependencies.values():
            if d.package_folder is None:
                continue
            dl = os.path.join(d.package_folder, "lib")
            if os.path.isdir(dl):
                deps.append(dl)
        ld = os.pathsep.join(deps + [lib_dir])
        self.run(
            f'LD_LIBRARY_PATH="{ld}" python3 "{test_script}" "{lib_dir}"'
        )
