#!/usr/bin/env python3
"""Conan recipe — libconfigini 22d700ab76 (plain Makefile, static C library).

libconfigini is a small INI-format configuration parser library written in
plain C. Upstream uses a hand-written GNU Makefile (no configure script):
  - `make all`          → libconfigini.a (static archive)
  - `make installdir=<D> install` → copies src/configini.h to <D>/include and
                                    libconfigini.a to <D>/lib
  - `make test`         → builds tests/test from tests/test.c and runs it
                          (runs Test1..Test4 user test functions)

Build notes:
  - R33: CC/CFLAGS come from the Conan toolchain (AutotoolsToolchain generates
    the conanbuild env); patch 0001 switches the upstream Makefile from
    `CC = gcc` to `CC ?=` so toolchain values are honored instead of the
    hard-coded gcc (which does not exist in the OHOS clang toolchain).
  - R26: static archive by default; upstream only ships a static lib.
  - E074: HarmonyOS SELinux forbids jobserver FIFO → all make with -j1.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibconfiginiConan(ConanFile):
    name = "libconfigini"
    version = "22d700ab76"
    description = "libconfigini - an INI formatted configuration parser library (C)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/taneryilmaz/libconfigini"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libconfigini is dependency-free (libc only)
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R33: compilers/flags come from the toolchain, never bare shell vars
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Build the static archive: make all → libconfigini.a
        self.run("make -j1 all", cwd=self.source_folder, env="conanbuild")
        # L0e: run the upstream test suite (tests/test.c, Test1..Test4).
        # Top-level `make test` first builds $(LIBARCH) then recurses into
        # tests/ and executes ./test (exit code is the test verdict).
        self.run("make -j1 test", cwd=self.source_folder, env="conanbuild")

    def package(self):
        # Upstream Makefile: make installdir=<DIR> install copies
        # src/configini.h → <DIR>/include and libconfigini.a → <DIR>/lib
        self.run(
            f"make -j1 installdir={self.package_folder} install",
            cwd=self.source_folder, env="conanbuild")

    def package_info(self):
        # libconfigini.a → link name "configini" (lib prefix stripped)
        self.cpp_info.libs = ["configini"]
