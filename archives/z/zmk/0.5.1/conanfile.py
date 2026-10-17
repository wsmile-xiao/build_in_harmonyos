#!/usr/bin/env python3
"""Conan recipe for zmk 0.5.1, a reusable GNU Make library."""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ZmkConan(ConanFile):
    name = "zmk"
    version = "0.5.1"
    description = "A reusable library for writing GNU Makefiles"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/zyga/zmk"
    url = "https://github.com/zyga/zmk"
    topics = ("build-system", "make", "makefile")
    package_type = "build-scripts"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_executables(self):
        executables = self.conf.get("tools.build:compiler_executables", default={}) or {}
        return executables.get("c") or "clang", executables.get("cpp") or "clang++"

    def _make_cc_aliases(self):
        # HarmonyOS ships clang/clang++ but has no `cc`/`c++` command names, and
        # the make binary baked into this image overrides its built-in CXX with a
        # build-machine path that does not exist here. Upstream's toolchain unit
        # tests assert the canonical defaults (CC=cc, CXX=c++/g++), so expose
        # wrappers under those names and keep the upstream assertions untouched.
        wrapper_dir = os.path.join(self.build_folder, "hmos-cc-aliases")
        os.makedirs(wrapper_dir, exist_ok=True)
        cc, cxx = self._compiler_executables()
        for name, target in (("cc", cc), ("c++", cxx)):
            wrapper = os.path.join(wrapper_dir, name)
            with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
                handle.write('#!/bin/sh\nexec "%s" "$@"\n' % target)
            os.chmod(wrapper, 0o755)
        return wrapper_dir

    def build(self):
        apply_conandata_patches(self)
 
        # Generate the manual pages and execute all upstream make-based tests.
        wrapper_dir = self._make_cc_aliases()
        env = f'PATH="{wrapper_dir}:$PATH"'
        self.run(f"{env} make all", cwd=self.source_folder)
        # Upstream's unit tests drive make with --dry-run and compare the exact
        # command lines against canonical host-toolchain text (CC=cc, no extra
        # flags). Conan exports CC plus the profile's CFLAGS/CPPFLAGS/LDFLAGS into
        # the build environment, which would leak into those expectations, so the
        # toolchain-related variables are dropped for this dry-run test step.
        self.run(
            f"{env} sh -c 'unset CC CXX CFLAGS CXXFLAGS CPPFLAGS OBJCFLAGS"
            " LDFLAGS LD AR AS RANLIB STRIP; make check'",
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc", "zmk"))
        copy(self, "NEWS", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc", "zmk"))

        include_dir = os.path.join(self.package_folder, "include")
        copy(self, "z.mk", src=self.source_folder, dst=include_dir)
        copy(self, "*.mk", src=os.path.join(self.source_folder, "zmk"), dst=os.path.join(include_dir, "zmk"))
        copy(self, "*.awk", src=os.path.join(self.source_folder, "zmk"), dst=os.path.join(include_dir, "zmk"))

        copy(self, "*.5", src=os.path.join(self.source_folder, "man"), dst=os.path.join(self.package_folder, "share", "man", "man5"))
        copy(self, "*", src=os.path.join(self.source_folder, "examples"), dst=os.path.join(self.package_folder, "share", "doc", "zmk", "examples"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
