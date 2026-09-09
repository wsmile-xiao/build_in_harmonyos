#!/usr/bin/env python3
"""Conan recipe for rpmalloc 1.4.5 — configure.py (Ninja) build system.

rpmalloc uses a Python-based Ninja generator (configure.py) with toolchain
modules under build/ninja/.  The OHOS adaptation:

  * clang.py upstream emits `-Wno-unsafe-buffer-usage`, unknown to clang 15;
    the flag is dropped in the applied patch so -Werror builds succeed.
  * atomic_cas_ptr used relaxed ordering for the deferred free span list,
    which raced on aarch64 (weak memory ordering) under -O2; the applied
    patch upgrades it to acq_rel/acquire semantics.

Compilers are taken from Conan conf (R33) and exported to the environment
because configure.py's clang toolchain reads CC/CXX/AR from os.environ.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RpmallocConan(ConanFile):
    name = "rpmalloc"
    version = "1.4.5"
    description = "Fast, lock-free, cross-platform memory allocator by Mattias Jansson"
    license = "MIT"
    homepage = "https://github.com/mjansson/rpmalloc"
    url = ""  # CI fills this

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

        # R33: compilers must come from Conan conf, not bare shell env vars.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c", "clang")
        cxx = comp_execs.get("cpp", "clang++")
        ar = comp_execs.get("ar", "ar")
        # configure.py's clang toolchain reads these from the environment.
        os.environ["CC"] = cc
        os.environ["CXX"] = cxx
        os.environ["AR"] = ar

        # Generate the Ninja build files, then build release arm64.
        # configure.py lives at the source root; run it from there so the
        # generated build.ninja and outputs land in the source tree.
        self.run(f"cd {self.source_folder} && python3 configure.py --target linux --toolchain clang --config release --arch arm64")
        self.run(f"cd {self.source_folder} && ninja")

    def package(self):
        copy(self, "*.h", os.path.join(self.source_folder, "rpmalloc"),
             os.path.join(self.package_folder, "include"))
        copy(self, "*.a", os.path.join(self.source_folder, "lib", "linux", "release", "arm64"),
             os.path.join(self.package_folder, "lib"))
        copy(self, "*.so", os.path.join(self.source_folder, "bin", "linux", "release", "arm64"),
             os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["rpmalloc"]
