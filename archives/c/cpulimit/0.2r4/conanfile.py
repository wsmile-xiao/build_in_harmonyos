#!/usr/bin/env python3
"""Conan recipe - cpulimit 0.2r4 (plain Makefile).

cpulimit is a C command-line tool that limits the CPU usage of a process.
The upstream tests are built and executed in build(), while test_package
verifies the installed command from a consumer's perspective.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CpulimitConan(ConanFile):
    name = "cpulimit"
    version = "0.2r4"
    description = "cpulimit - a CPU limiter for Linux/OHOS"
    license = "GPL-2.0"
    homepage = "https://github.com/opsengine/cpulimit"
    url = "https://github.com/opsengine/cpulimit"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # cpulimit has no external dependencies (only libc).
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: use the compiler selected by the Conan profile.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or "clang"

        # The top-level Makefile builds src/ and tests/; -j1 keeps the
        # upstream plain Makefiles deterministic.
        self.run(f"make -j1 CC={cc}", cwd=self.source_folder)

        # Upstream README specifies tests/process_iterator_test as its test.
        self.run(
            os.path.join("tests", "process_iterator_test"),
            cwd=self.source_folder,
        )

    def package(self):
        # cpulimit is a command-line tool: install the binary to bin/.
        copy(
            self,
            "cpulimit",
            src=os.path.join(self.source_folder, "src"),
            dst=os.path.join(self.package_folder, "bin"),
        )

    def package_info(self):
        # cpulimit is a command-line tool, not a library.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
