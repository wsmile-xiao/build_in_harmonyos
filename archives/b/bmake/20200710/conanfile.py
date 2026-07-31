#!/usr/bin/env python3
"""Exploratory Conan build probe for bmake 20200710 on OpenHarmony."""

import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class BmakeConan(ConanFile):
    name = "bmake"
    version = "20200710"
    description = "Portable make tool derived from NetBSD make"
    license = "BSD-2-Clause"
    homepage = "https://www.crufty.net/help/sjg/bmake.html"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # boot-strap performs the configure, build and install stages itself.
        # --install-host-target keeps its generated binaries below the prefix.
        compiler = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c", "clang")
        prefix = os.path.join(self.build_folder, "stage")
        self.run(
            'CC="{}" sh boot-strap --prefix="{}" --install-host-target '
            "-DWITH_PROG_VERSION".format(compiler, prefix),
            cwd=self.source_folder,
        )

    def package(self):
        destination = os.path.join(self.package_folder, "bin")
        for root, _, files in os.walk(os.path.join(self.build_folder, "stage")):
            if os.path.basename(root) == "bin":
                for filename in files:
                    if filename.startswith("bmake"):
                        copy(self, filename, src=root, dst=destination, keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
