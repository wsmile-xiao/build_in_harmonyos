#!/usr/bin/env python3
"""Conan recipe — cpulimit 0.2 (Makefile project, no configure).

cpulimit is a simple C command-line tool that limits CPU usage of processes.
Build system: plain Makefile (no configure script).
Output: src/cpulimit binary (command-line tool, not a library).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CpulimitConan(ConanFile):
    name = "cpulimit"
    version = "0.2"
    description = "cpulimit - a CPU limiter for Linux/OHOS"
    license = "GPL-2.0"
    homepage = "https://github.com/opsengine/cpulimit"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # cpulimit has no external dependencies (only libc)
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # cpulimit uses a plain Makefile (no configure script).
        # The top-level Makefile delegates to src/ and tests/.
        # We only need the cpulimit binary from src/.
        # R9: Always use -j1
        # CC and CXX are set by Conan profile (tools.build:compiler_executables)
        # The source already has #define _GNU_SOURCE from patch, so CFLAGS is minimal
        src_dir = os.path.join(self.source_folder, "src")
        self.run(f"make -C {src_dir} -j1")

    def package(self):
        # cpulimit is a command-line tool — install the binary to bin/
        copy(self, "cpulimit", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # cpulimit is a command-line tool, not a library.
        # No libs to declare — consumers use it as a binary tool.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
