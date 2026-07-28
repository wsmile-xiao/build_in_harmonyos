#!/usr/bin/env python3
"""Conan recipe — nerdfetch 8.5.5

nerdfetch is a POSIX shell script that displays system/OS information
in a fetch-style output (single-file CLI tool).
Build system: none (pure shell script, no compilation required).
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class NerdfetchConan(ConanFile):
    name = "nerdfetch"
    version = "8.5.5"
    description = "POSIX shell script that displays system info in a fetch-style output"
    license = "MIT"
    homepage = "https://github.com/ThatOneCalculator/NerdFetch"
    url = ""

    settings = "os", "arch"
    package_type = "application"

    def validate(self):
        pass

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        pass

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, "nerdfetch", src=self.source_folder, dst=bindir)
        nerdfetch_dst = os.path.join(bindir, "nerdfetch")
        st = os.stat(nerdfetch_dst)
        os.chmod(nerdfetch_dst, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
