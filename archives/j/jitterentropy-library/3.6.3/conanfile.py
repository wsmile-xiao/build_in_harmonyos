#!/usr/bin/env python3
"""Conan recipe for jitterentropy-library 3.6.3 — CPU jitter entropy library."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class JitterentropyLibraryConan(ConanFile):
    name = "jitterentropy-library"
    version = "3.6.3"
    description = "CPU jitter entropy library for random number generation"
    license = "BSD-3-Clause"
    homepage = "https://github.com/smuellerDD/jitterentropy-library"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "")
        if not ar:
            _bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            ar = os.path.join(_bindir, "llvm-ar") if _bindir else "llvm-ar"

        # Build from the source folder where the Makefile is
        # R9: Always use -j1
        # Override LIBMAJOR/MINOR/PATCH since egrep may not be available in CI
        make_vars = (
            f"CC={cc} AR={ar} "
            f"LIBMAJOR=3 LIBMINOR=6 LIBPATCH=3 "
            f"LIBVERSION=3.6.3"
        )
        if self.options.shared:
            self.run(f"make -C {self.source_folder} {make_vars} -j1")
        else:
            self.run(f"make -C {self.source_folder} {make_vars} libjitterentropy.a -j1")

    def package(self):
        # Copy headers from source root
        copy(self, "jitterentropy.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "jitterentropy-base-user.h", self.source_folder, os.path.join(self.package_folder, "include"))

        if self.options.shared:
            # Copy shared library and create symlinks
            copy(self, "libjitterentropy.so.3.6.3", self.source_folder, os.path.join(self.package_folder, "lib"))
            # Create symlinks: libjitterentropy.so.3 -> libjitterentropy.so.3.6.3
            lib_dir = os.path.join(self.package_folder, "lib")
            self._create_symlink(lib_dir, "libjitterentropy.so.3", "libjitterentropy.so.3.6.3")
            self._create_symlink(lib_dir, "libjitterentropy.so", "libjitterentropy.so.3")
        else:
            copy(self, "libjitterentropy.a", self.source_folder, os.path.join(self.package_folder, "lib"))

    def _create_symlink(self, dir_path, link_name, target_name):
        link_path = os.path.join(dir_path, link_name)
        target_path = target_name
        if os.path.islink(link_path) or os.path.exists(link_path):
            os.remove(link_path)
        os.symlink(target_path, link_path)

    def package_info(self):
        self.cpp_info.libs = ["jitterentropy"]
        if not self.options.shared:
            self.cpp_info.system_libs = ["pthread", "rt"]
