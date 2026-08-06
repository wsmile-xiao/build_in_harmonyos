#!/usr/bin/env python3
"""Conan recipe for fastjar 0.98 — Autotools-based JAR manipulation tool.

fastjar is a fast Java Archive (JAR) file manipulation tool that provides
`fastjar` and `grepjar` command-line utilities for creating, extracting,
and searching JAR files.

Build system: autotools (configure + make)
Product type: application (CLI executables)
Dependencies: zlib
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class FastjarConan(ConanFile):
    name = "fastjar"
    version = "0.98"
    description = "Fast Java Archive (JAR) file manipulation tool"
    license = "GPL-2.0"
    homepage = "https://savannah.nongnu.org/projects/fastjar/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix shebangs for OHOS: /bin/sh -> /system/bin/sh
        if self.settings.os == "OHOS":
            for script in ["configure", "compile", "install-sh", "config.guess", "config.sub"]:
                path = os.path.join(self.source_folder, script)
                if os.path.exists(path):
                    replace_in_file(self, path, "#! /bin/sh", "#!/system/bin/sh", strict=False)
                    replace_in_file(self, path, "#!/bin/sh", "#!/system/bin/sh", strict=False)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
