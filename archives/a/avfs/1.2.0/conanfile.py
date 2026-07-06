#!/usr/bin/env python3
"""Conan recipe — avfs 1.2.0 (A Virtual File System).

AVFS is a virtual file system library that provides transparent access
to archive files (tar, zip, gzip, bzip2, etc.) as if they were directories.

Build system: autotools (configure + make)
License: LGPL-2.0 (library), GPL-2.0 (tools)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AvfsConan(ConanFile):
    name = "avfs"
    version = "1.2.0"
    description = "A Virtual File System - transparent access to archive files as directories"
    license = "LGPL-2.0"
    homepage = "https://savannah.nongnu.org/projects/avfs/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # avfs has no external Conan dependencies (zlib and bzip2 are bundled)
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # avfs is NOT a system同名库, so R26 static requirement does not apply.
        # Default dynamic linking, managed by Conan dependency chain.
        # R32: OS check uses in ("Linux", "OHOS") pattern
        if self.settings.os in ("Linux", "OHOS"):
            tc.extra_ldflags.append("-lpthread")
            tc.extra_ldflags.append("-ldl")
        tc.generate()

    def build(self):
        # E001: On OHOS, cc/c++ symlinks don't exist, only clang/clang++
        import os
        os.environ["CC"] = "clang"
        os.environ["CXX"] = "clang++"
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["avfs"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl"]
