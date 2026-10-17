#!/usr/bin/env python3
"""Conan recipe — complete-striped-smith-waterman 1.2.5.

Complete-Striped-Smith-Waterman-Library (SSW): SIMD-accelerated
Smith-Waterman sequence alignment library (C + C++ API).

Build notes:
  - upstream ships a hand-written Makefile only (no configure/CMake);
  - upstream source tree: <root>/src/<Makefile, ssw.*, main.c ...> —
    after get(strip_root=True) the Makefile lives in source_folder/src,
    so build()/package() must use the src/ subdirectory;
  - the Makefile hardcodes CC=gcc/CXX=g++; the recipe passes the Conan
    compiler on the make command line (command-line vars override the
    makefile assignments), and zlib include/lib dirs via CPPFLAGS/LDFLAGS
    (main.c / example compile <zlib.h> and link -lz);
  - upstream builds libssw.so (shared) only — no static archive target,
    so `shared` defaults to True and the .so is always produced;
  - ssw.h includes "sse2neon.h" (pure-header SSE2->NEON translation), so
    sse2neon.h is installed alongside the public headers for consumers;
  - R9: make -j1 (OHOS build constraint); R33: compiler from Conan conf.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class CompleteStripedSmithWatermanConan(ConanFile):
    name = "complete-striped-smith-waterman"
    version = "1.2.5"
    description = ("Complete-Striped-Smith-Waterman-Library (SSW): SIMD "
                   "Smith-Waterman sequence alignment library")
    license = "MIT"
    homepage = "https://github.com/mengyao/Complete-Striped-Smith-Waterman-Library"
    url = "https://github.com/mengyao/Complete-Striped-Smith-Waterman-Library"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # main.c / examples include <zlib.h> and link -lz (kseq gzip reads).
        self.requires("zlib/1.3.1")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "complete-striped-smith-waterman is only supported on "
                "Linux/OHOS, not " + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Feed zlib include/lib dirs to the plain Makefile build (upstream
        # has no pkg-config; CPPFLAGS/LDFLAGS are referenced by its implicit
        # link rules: `$(CC) -o $@ ... $(CFLAGS) $(LDFLAGS) -lm -lz`).
        env = Environment()
        for dep in self.dependencies.values():
            for incdir in dep.cpp_info.includedirs:
                env.append_path("CPPFLAGS", "-I" + incdir)
            for libdir in dep.cpp_info.libdirs:
                env.append_path("LDFLAGS", "-L" + libdir)
        env.vars(self, scope="build").save_script("conanbuild_flags")

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler from Conan conf (never bare ${CC} shell vars).
        try:
            compiler_exes = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
        except Exception:
            compiler_exes = {}
        if isinstance(compiler_exes, dict):
            cc = compiler_exes.get("c") or "clang"
            cxx = compiler_exes.get("cpp") or "clang++"
        else:
            cc, cxx = "clang", "clang++"
        # default target builds ssw_test + example_c + example_cpp + libssw.so;
        # command-line CC/CXX override the hardcoded gcc/g++ in the Makefile.
        # R9: -j1 (OHOS build constraint).
        # Makefile lives in source_folder/src (upstream <root>/src layout).
        self.run("make -j1 CC=%s CXX=%s default" % (cc, cxx),
                 cwd=os.path.join(self.source_folder, "src"),
                 env="conanbuild")

    def package(self):
        src_dir = os.path.join(self.source_folder, "src")
        copy(self, "libssw.so", src=src_dir,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        for header in ("ssw.h", "ssw_cpp.h", "sse2neon.h"):
            copy(self, header, src=src_dir,
                 dst=os.path.join(self.package_folder, "include"),
                 keep_path=False)
        if os.path.exists(os.path.join(src_dir, "LICENSE")):
            copy(self, "LICENSE", src=src_dir,
                 dst=os.path.join(self.package_folder, "licenses"),
                 keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["ssw"]
        self.cpp_info.requires = ["zlib::zlib"]
        self.cpp_info.set_property("cmake_file_name", "complete-striped-smith-waterman")
        self.cpp_info.set_property("cmake_target_name",
                                   "complete-striped-smith-waterman::complete-striped-smith-waterman")