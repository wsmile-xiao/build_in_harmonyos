#!/usr/bin/env python3
"""Exploratory Conan build probe for bmake 20240606 on OpenHarmony."""

import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class BmakeConan(ConanFile):
    name = "bmake"
    version = "20240606"
    description = "Portable make tool derived from NetBSD make"
    license = "BSD-2-Clause"
    homepage = "https://www.crufty.net/help/sjg/bmake.html"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source_data = self.conan_data["sources"][self.version]
        last_error = None
        for url in source_data["urls"]:
            try:
                get(self, url=url, strip_root=True)
                return
            except Exception as error:
                last_error = error
                self.output.warning("Unable to download {}: {}".format(url, error))
        raise RuntimeError("Unable to download bmake source from configured mirrors") from last_error

    def build(self):
        # boot-strap compiles the tool without requiring a pre-existing make.
        # On OHOS it also reveals whether generated host executables require
        # explicit signing before boot-strap can continue.
        prefix = os.path.join(self.build_folder, "stage")
        self.run('sh boot-strap --prefix="{}"'.format(prefix), cwd=self.source_folder)

    def package(self):
        stage_bin = os.path.join(self.build_folder, "stage", "bin")
        copy(self, "bmake", src=stage_bin, dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
