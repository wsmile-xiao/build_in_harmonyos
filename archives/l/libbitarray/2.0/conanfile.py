#!/usr/bin/env python3
"""Conan recipe for libbitarray 2."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibbitarrayConan(ConanFile):
    name = "libbitarray"
    version = "2.0"
    description = "Portable C bit array library"
    license = "CC0-1.0"
    homepage = "https://github.com/noporpoise/BitArray"
    url = "https://github.com/noporpoise/BitArray"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [False]}
    default_options = {"shared": False}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = self._tool_command(compilers.get("c"), "clang")
        cxx = self._tool_command(compilers.get("cpp"), "clang++")
        ar = self._tool_command(compilers.get("ar"), "llvm-ar")
        ranlib = self._tool_command(compilers.get("ranlib"), "llvm-ranlib")

        make_vars = self._make_vars(cc, cxx, ar, ranlib)
        self.run(f"make -j1 {make_vars}", cwd=self.source_folder)
        self.run(f"make -j1 {make_vars} test", cwd=self.source_folder)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        for header in ("bit_array.h", "bit_macros.h", "bar.h"):
            copy(self, header, src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "libbitarr.a", src=self.source_folder, dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["bitarr"]
        self.cpp_info.set_property("cmake_file_name", "libbitarray")
        self.cpp_info.set_property("cmake_target_name", "libbitarray::libbitarray")

    def _make_vars(self, cc, cxx, ar, ranlib):
        make_vars = [
            f'CC="{cc}"',
            f'CXX="{cxx}"',
            f'AR="{ar}"',
            f'RANLIB="{ranlib}"',
        ]
        if self.settings.os == "OHOS":
            make_vars.append('PTHREAD_LIBS="-pthread"')
        return " ".join(make_vars)

    def _tool_command(self, configured, fallback):
        tool = configured or shutil.which(fallback) or fallback
        if os.path.isfile(tool):
            try:
                with open(tool, "rb") as handle:
                    if handle.read(2) == b"#!":
                        return f"sh {tool}"
            except OSError:
                pass
        return tool
