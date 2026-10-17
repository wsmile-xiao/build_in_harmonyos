#!/usr/bin/env python3
"""Conan recipe - tstools 1.13-git20151030.

tstools is a collection of MPEG TS/PS/ES command-line tools.  The project
uses a plain GNU Makefile and builds a static library plus consumer tools.
The upstream ``make test`` target runs the two list/unit regression tests.
"""

import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class TstoolsConan(ConanFile):
    name = "tstools"
    version = "1.13-git20151030"
    description = "Command-line tools for MPEG TS, PS and ES streams"
    license = "MPL-1.1"
    homepage = "https://github.com/kynesim/tstools"
    url = "https://github.com/kynesim/tstools"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or "clang"

        # Keep the upstream Makefiles serial and use the cross compiler
        # selected by the Conan profile.
        # The upstream shared library target is neither installed nor used by
        # the command-line tools. Suppress that optional target so the OHOS
        # linker does not need host-only shared-library defaults.
        self.run(f"make -j1 CC={cc} SHARED_LIB=", cwd=self.source_folder)
        self.run(f"make test CC={cc}", cwd=self.source_folder)

    def package(self):
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "bin"),
            dst=os.path.join(self.package_folder, "bin"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
