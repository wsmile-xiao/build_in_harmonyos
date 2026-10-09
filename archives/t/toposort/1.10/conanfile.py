#!/usr/bin/env python3
"""Conan recipe for the pure-Python toposort 1.10 library."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class ToposortConan(ConanFile):
    name = "toposort"
    version = "1.10"
    description = "Pure-Python topological sorting of dependency graphs"
    license = "Apache-2.0"
    homepage = "https://gitlab.com/ericvsmith/toposort"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # The upstream tests use unittest and need only the standard library.
        # Keep them unchanged and run them against the unpacked source module.
        self.run("PYTHONPATH=src python3 test/test_toposort.py",
                 cwd=self.source_folder)

    def package(self):
        source = os.path.join(self.source_folder, "src")
        module = copy(self, "toposort.py", src=source,
                      dst=os.path.join(self.package_folder, "lib", "python"))
        if not module:
            raise ConanException("toposort.py was not packaged")
        license_file = copy(self, "LICENSE.txt", src=self.source_folder,
                            dst=os.path.join(self.package_folder, "licenses"),
                            keep_path=False)
        if not license_file:
            raise ConanException("LICENSE.txt was not packaged")

    def package_id(self):
        # The package contains Python source only and has no ABI-specific data.
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, "lib", "python"))
