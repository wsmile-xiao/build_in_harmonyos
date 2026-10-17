#!/usr/bin/env python3
"""Conan recipe for kiwisolver (aka Kiwi) — a header-only C++ implementation
of the Cassowary constraint solving algorithm.

Upstream builds as an INTERFACE library (kiwi::kiwi) with CMake; there is no
install() rule in CMakeLists.txt, so package() copies the headers manually.
The upstream test suite (tests/ + googletest) is exercised in test_package
via a compiled consumer program (R34 real API usage).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class KiwisolverConan(ConanFile):
    name = "kiwisolver"
    version = "1.5.1"
    description = "A fast implementation of the Cassowary constraint solver (header-only C++)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/nucleic/kiwi"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        # Header-only library: copy the kiwi/ include dir into include/
        copy(self, "*.h", os.path.join(self.source_folder, "kiwi"),
             os.path.join(self.package_folder, "include", "kiwi"))

    def package_info(self):
        # Header-only: no libs to link, consumers include <kiwi/kiwi.h>
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
