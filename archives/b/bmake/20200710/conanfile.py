#!/usr/bin/env python3
"""Exploratory Conan build probe for bmake 20200710 on OpenHarmony."""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class BmakeConan(ConanFile):
    name = "bmake"
    version = "20200710"
    description = "Portable make tool derived from NetBSD make"
    license = "BSD-2-Clause"
    homepage = "https://www.crufty.net/help/sjg/bmake.html"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # Upstream requires boot-strap to run from the directory containing
        # the unpacked bmake source. It then creates and builds in its own
        # object directory, leaving the source tree untouched.
        compiler = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c", "clang")
        apply_conandata_patches(self)
        prefix = os.path.join(self.build_folder, "stage")
        self.run(
            'SKIP_TESTS=1 HOST_TARGET=ohos-aarch64 CC="{}" sh "{}" --prefix="{}" --install-host-target '
            "--with-machine=ohos -DWITH_PROG_VERSION".format(
                compiler, os.path.join(self.source_folder, "boot-strap"), prefix
            ),
            cwd=os.path.dirname(self.source_folder),
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
