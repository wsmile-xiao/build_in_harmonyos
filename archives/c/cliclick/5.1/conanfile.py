#!/usr/bin/env python3
"""Conan recipe for the cliclick 5.1 OHOS port (plain Makefile project).

Upstream cliclick is a macOS-only Objective-C/Cocoa command-line tool.
The OHOS port applies one additive patch that introduces a pure-C backend
(ohos/) built on the OpenHarmony input-injection C API; the recipe builds
only that backend. There are no Conan dependencies: libohinput.so is an
OpenHarmony system/SDK library resolved by the OHOS clang against the
device sysroot.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class CliclickConan(ConanFile):
    name = "cliclick"
    version = "5.1"
    description = "Command-line mouse and keyboard automation tool (OHOS OH_Input backend)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/BlueM/cliclick"
    url = ""  # CI fills this
    topics = ("cli", "automation", "input", "ohos")

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        ohos_dir = os.path.join(self.source_folder, "ohos")
        build_cmd = 'make -C "%s" CC="%s" CFLAGS="-O2"' % (ohos_dir, cc)
        self.run(build_cmd)

    def package(self):
        copy(self, "cliclick",
             src=os.path.join(self.source_folder, "ohos"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
