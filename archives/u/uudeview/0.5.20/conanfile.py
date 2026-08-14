#!/usr/bin/env python3
"""Conan recipe — uudeview 0.5.20 (autotools)"""

import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class UudeviewConan(ConanFile):
    name = "uudeview"
    version = "0.5.20"
    description = "UUDeview is a program that helps you transmit and receive binary files over the Internet, using email or newsgroups."
    license = "GPL-2.0-or-later"
    homepage = "http://www.fpx.de/fp/Software/UUDeview/"

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-minews")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E165: Fix shebang for OHOS only
        if self.settings.os == "OHOS":
            self.run("sed -i '1s|#!/bin/sh|#!/system/bin/sh|' configure", cwd=self.source_folder)
            self.run("sed -i '1s|#!/bin/bash|#!/data/service/hnp/bin/bash|' configure", cwd=self.source_folder)
            self.run("sed -i '1s|#!/bin/sh|#!/system/bin/sh|' install-sh", cwd=self.source_folder)
        # uudeview's Makefile uses cd subdir; make, which breaks with
        # Conan's Autotools build-folder separation. Use self.run() directly.
        # Source conanbuild.sh to apply AutotoolsToolchain env (CFLAGS, --host, etc.)
        build_info = os.path.join(self.generators_folder, "conanbuild.sh")
        self.run(f". {build_info} && ./configure --prefix={self.package_folder} --disable-minews",
                 cwd=self.source_folder)
        self.run(f". {build_info} && make -j1", cwd=self.source_folder)

    def package(self):
        self.run("make install", cwd=self.source_folder)
        copy(self, "uudeview.h", src=os.path.join(self.source_folder, "uulib"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "uuint.h", src=os.path.join(self.source_folder, "uulib"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libuu.a", src=os.path.join(self.source_folder, "uulib"),
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["uu"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        bindir = os.path.join(self.package_folder, "bin")
        self.output.info(f"Appending PATH environment variable: {bindir}")
        self.runenv_info.prepend_path("PATH", bindir)
        self.buildenv_info.prepend_path("PATH", bindir)
