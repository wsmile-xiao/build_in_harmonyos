#!/usr/bin/env python3
"""Conan recipe — tommyds 3.0

TommyDS is a header + single-C aggregate file C data-structure library
(tommyds/tommy.c includes all implementations; headers live in tommyds/).
Upstream ships only a plain Makefile with NO configure and NO install target.

This recipe builds a static library libtommy.a using the Conan toolchain
compiler and installs the public headers into include/tommyds/. The upstream
tommycheck self-test (check.c) is built and executed inside build() as an
upstream test gate (R34: the package is genuinely exercised).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class TommydsConan(ConanFile):
    name = "tommyds"
    version = "3.0"
    description = "C 高性能数据结构和容器库 — 数组、哈希表、树、trie 等，为高性能设计"
    license = "BSD-2-Clause"
    homepage = "https://www.tommyds.it"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        # R32: OHOS platform compatibility
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tommyds is supported only on Linux/OHOS, got: {self.settings.os}")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler from Conan conf — never bare ${CC}/${CFLAGS} shell vars
        comp_execs = self.conf.get("tools.build:compiler_executables",
                                   default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        ar = comp_execs.get("ar") or "llvm-ar"
        ranlib = comp_execs.get("ranlib") or "llvm-ranlib"

        src_dir = self.source_folder
        build_dir = self.build_folder

        # Upstream Makefile CFLAGS contain -march=native (breaks cross/CI);
        # use generic flags instead.
        cflags = "-fPIC -Wall"
        if str(self.settings.build_type) == "Release":
            cflags += " -O3"
        else:
            cflags += " -O0 -g"

        # 1) Build the static library from the aggregate source file.
        obj = os.path.join(build_dir, "tommy.o")
        lib = os.path.join(build_dir, "libtommy.a")
        self.run(f'"{cc}" {cflags} -c "{os.path.join(src_dir, "tommyds", "tommy.c")}" -o "{obj}"')
        self.run(f'"{ar}" rcs "{lib}" "{obj}"')
        self.run(f'"{ranlib}" "{lib}"')

        # 2) Upstream self-check: build + run tommycheck (comprehensive
        #    correctness check of all data structures). Genuinely exercises
        #    the library — failing it fails the package build.
        checkbin = os.path.join(build_dir, "tommycheck")
        self.run(f'"{cc}" -O2 "{os.path.join(src_dir, "check.c")}" "{lib}" -o "{checkbin}" -lm')
        self.run(f'"{checkbin}"')

    def package(self):
        # Public headers are the tommyds/*.h set; install as include/tommyds/
        copy(self, "*.h", os.path.join(self.source_folder, "tommyds"),
             os.path.join(self.package_folder, "include", "tommyds"))
        copy(self, "libtommy.a", self.build_folder,
             os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["tommy"]
        self.cpp_info.includedirs = ["include"]
