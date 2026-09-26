#!/usr/bin/env python3
"""Conan recipe for symfpu 0.0-git.40bdec00 (OHOS PC adaptation).

symfpu (The Symbolic Floating Point Unit) is a C++11 header/template library
implementing the SMT-LIB theory of IEEE-754 floating point in terms of
bit-vector operations.  Upstream build is a plain Makefile that expects the
checkout to live in a directory named `symfpu/` (sub-Makefiles add -I../..).

Adaptation notes (OHOS aarch64):
  - upstream `flags` passes x86-only options (-msse2 -mfpmath=sse -mfma
    -mno-fma4); removed via patches/0002-flags.patch (clang rejects
    "-mfpmath=sse" on aarch64).
  - applications/test.cpp includes glibc-only <ieee754.h>; replaced with a
    portable single-precision bit-layout union via patches/0001-*.patch.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SymfpuConan(ConanFile):
    name = "symfpu"
    version = "0.0-git.40bdec00"
    description = "SymFPU: The Symbolic Floating Point Unit (SMT-LIB FP theory in bit-vector terms)"
    license = "GPL-3.0-only OR BSD-3-Clause"
    homepage = "https://github.com/martin-cs/symfpu"
    url = "https://github.com/martin-cs/symfpu"

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

        # R33: compilers come from Conan conf, never from bare shell env vars.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = comp_execs.get("cpp") or comp_execs.get("cxx") or "clang++"
        ar = comp_execs.get("ar") or "llvm-ar"
        ranlib = comp_execs.get("ranlib") or "llvm-ranlib"

        # Upstream Makefile expects the sources under a directory literally
        # named `symfpu` (sub-Makefiles use -I../.. relative to it).  Create a
        # symlink from the source_folder's parent so the -I../.. includes
        # resolve to ./symfpu/... even under a hashed conan source dir.
        parent = os.path.dirname(os.path.normpath(self.source_folder))
        link = os.path.join(parent, "symfpu")
        if not os.path.islink(link) and not os.path.exists(link):
            os.symlink(self.source_folder, link)

        # R9: -j1.  Serial traversal also avoids the top-level implicit rule
        # racing the sub-directory object builds (upstream Makefile quirk).
        self.run(f"make -C {link} CXX={cxx} AR={ar} RANLIB={ranlib} -j1")

    def package(self):
        # Headers keep the upstream layout: include/symfpu/{baseTypes,core,utils,applications}
        for subdir in ("baseTypes", "core", "utils", "applications"):
            copy(self, "*.h",
                 os.path.join(self.source_folder, subdir),
                 os.path.join(self.package_folder, "include", "symfpu", subdir))
        # Static archive built by upstream Makefile: symfpu.a -> libsymfpu.a
        copy(self, "symfpu.a", self.source_folder,
             os.path.join(self.package_folder, "lib"))
        os.rename(os.path.join(self.package_folder, "lib", "symfpu.a"),
                  os.path.join(self.package_folder, "lib", "libsymfpu.a"))
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["symfpu"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "symfpu")
        self.cpp_info.set_property("cmake_target_name", "symfpu::symfpu")