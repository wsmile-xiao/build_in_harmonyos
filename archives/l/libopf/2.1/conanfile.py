#!/usr/bin/env python3
"""Conan recipe — libopf 2.1 (Makefile, C)

LibOPF — Optimum-Path Forest (OPF) classifiers library plus companion
CLI tools (opf_train, opf_classify, opf_split, ...).

Build system: plain Makefile.  Upstream has no configure script (the
`configure` file only appends OPF_DIR to ~/.bashrc) and no `install`
target, so this recipe overrides CC from the Conan toolchain and
installs lib/libOPF.a, include headers and the built tools manually.

OHOS/ARM64 portability fix (patched in patches/): the SNode.status and
SNode.relevant fields are `char`, which is UNSIGNED on aarch64 — the
code compares status against NIL (== -1), which never matches, corrupting
opf_SplitSubgraph.  The patch makes them `signed char`.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibopfConan(ConanFile):
    name = "libopf"
    version = "2.1"
    description = "Optimum-Path Forest (OPF) classifiers library in C"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/jppbsi/LibOPF"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libopf supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: take the compiler from the Conan toolchain config, never from
        # an undefined shell variable (the upstream Makefile hardcodes CC=gcc,
        # which does not exist on the OHOS SDK toolchain).
        comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cc = comp.get("c", "clang") if comp else "clang"

        self.run(f"make -j1 CC='{cc}'", env="conanbuild", cwd=self.source_folder)

    def package(self):
        src = self.source_folder
        pkg = self.package_folder
        # Static library: lib/libOPF.a
        copy(self, "libOPF.a", src=os.path.join(src, "lib"),
             dst=os.path.join(pkg, "lib"), keep_path=False)
        # Headers: include/OPF.h + include/util/*.h
        copy(self, "*.h", src=os.path.join(src, "include"),
             dst=os.path.join(pkg, "include"), keep_path=True)
        # CLI tools built into bin/ (opf_* tools)
        copy(self, "*", src=os.path.join(src, "bin"),
             dst=os.path.join(pkg, "bin"), keep_path=False)
        # Additional tools built into tools/ (statistics, txt2opf, ...)
        for _t in ("statistics", "txt2opf", "opf2txt", "opf_check",
                   "opf2svm", "svm2opf", "kmeans"):
            if os.path.exists(os.path.join(src, "tools", _t)):
                copy(self, _t, src=os.path.join(src, "tools"),
                     dst=os.path.join(pkg, "bin"), keep_path=False)

    def package_info(self):
        # OPF.h 依赖 include/util/*.h（上游 Makefile 用 -Iinclude -Iinclude/util）
        self.cpp_info.includedirs = ["include", "include/util"]
        self.cpp_info.libs = ["OPF"]
        self.cpp_info.bindirs = ["bin"]