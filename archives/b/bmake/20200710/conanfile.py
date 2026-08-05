#!/usr/bin/env python3
"""Exploratory Conan build probe for bmake 20200710 on OpenHarmony."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
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

    def validate(self):
        if str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration(
                "bmake/20200710 currently supports only OHOS aarch64"
            )

    def build(self):
        # Upstream requires boot-strap to run from the directory containing
        # the unpacked bmake source. It then creates and builds in its own
        # object directory, leaving the source tree untouched.
        compiler = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c", "clang")
        arch = {"armv8": "aarch64", "aarch64": "aarch64"}[
            str(self.settings.arch)
        ]
        host_target = f"ohos-{arch}"
        apply_conandata_patches(self)
        prefix = os.path.join(self.build_folder, "stage")
        self.run(
            'HOST_TARGET="{}" MK_AUTO_OBJ=no CC="{}" sh "{}" --prefix="{}" --install-host-target '
            "--with-machine=ohos -DWITH_PROG_VERSION".format(
                host_target,
                compiler,
                os.path.join(self.source_folder, "boot-strap"),
                prefix,
            ),
            cwd=os.path.dirname(self.source_folder),
        )

    def package(self):
        stage = os.path.join(self.build_folder, "stage")
        destination = os.path.join(self.package_folder, "bin")
        for root, _, files in os.walk(stage):
            if os.path.basename(root) == "bin":
                for filename in files:
                    if filename.startswith("bmake"):
                        copy(self, filename, src=root, dst=destination, keep_path=False)
        copy(
            self,
            "*",
            src=os.path.join(stage, "share"),
            dst=os.path.join(self.package_folder, "share"),
            keep_path=True,
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.define_path(
            "MAKESYSPATH", os.path.join(self.package_folder, "share", "mk")
        )
