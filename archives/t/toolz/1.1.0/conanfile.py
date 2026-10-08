#!/usr/bin/env python3
"""Conan recipe for the pure Python toolz 1.1.0 library."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class ToolzConan(ConanFile):
    name = "toolz"
    version = "1.1.0"
    description = "List processing tools and functional utilities"
    license = "BSD-3-Clause"
    homepage = "https://github.com/pytoolz/toolz"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            extract_filter="data")

    def package(self):
        source = self.source_folder
        target = os.path.join(self.package_folder, "lib", "python")
        for package in ("toolz", "tlz"):
            if not copy(self, "*.py", src=os.path.join(source, package),
                        dst=os.path.join(target, package), keep_path=True):
                raise ConanException(f"toolz source package is missing: {package}")
        if not copy(self, "LICENSE.txt", src=source,
                    dst=os.path.join(self.package_folder, "licenses"),
                    keep_path=False):
            raise ConanException("toolz LICENSE.txt was not packaged")

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, "lib", "python"))
