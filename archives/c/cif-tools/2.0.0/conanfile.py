#!/usr/bin/env python3
"""Conan recipe for cif-tools 2.0.0 — CMake.

A suite of programs to manipulate and examine mmCIF / PDB files
(PDB-REDO): pdb2cif, cif2pdb, cif-diff, cif-merge, cif-validate, mmcql.

Consumer contract notes (all verified against the 2.0.0 source):

* cif-tools' CMakeLists does ``find_package(cifpp 10 QUIET)`` and links
  ``cifpp::cifpp``. The published libcifpp/10.0.4 recipe only sets
  ``pkg_config_name=cifpp`` (no cmake_file_name/cmake_target_name), so
  CMakeDeps would otherwise emit ``libcifpp-config.cmake`` — we override the
  dependency's CMake naming in generate() so ``find_package(cifpp)`` works.
* Same for libmcfp/1.4.2 (header-only, upstream target ``mcfp``): overridden
  to ``find_package(mcfp)`` + ``mcfp::mcfp``; otherwise the upstream CMake
  falls back to CPMAddPackage() which downloads from the network (forbidden
  in the OHOS CI sandbox).
* mrc/1.3.17 is optional upstream (``find_package(mrc QUIET)``, USE_RSRC).
  Its recipe already sets cmake_file_name=mrc, so no override needed.
* ``readln`` is vendored inside the tarball (readln/readln.cpp); no external
  dependency.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class CifToolsConan(ConanFile):
    name = "cif-tools"
    version = "2.0.0"
    description = "Suite of programs to manipulate and examine mmCIF and PDB files"
    license = "BSD-2-Clause"
    homepage = "https://github.com/PDB-REDO/cif-tools"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # find_package(cifpp 10) / cifpp::cifpp — required
        self.requires("libcifpp/10.0.4")
        # find_package(mcfp) / mcfp::mcfp — required (else CPM network fetch)
        self.requires("libmcfp/1.4.2")
        # find_package(mrc QUIET) — optional upstream; published, so provide it
        self.requires("mrc/1.3.17")

    def layout(self):
        basic_layout(self)

    def generate(self):
        # Override the CMake naming of the two deps so the upstream
        # find_package(cifpp) / find_package(mcfp) calls resolve to conan
        # packages instead of the bundled libcifpp subtree / CPM download.
        deps = CMakeDeps(self)
        deps.set_property("libcifpp", "cmake_file_name", "cifpp")
        deps.set_property("libcifpp", "cmake_target_name", "cifpp::cifpp")
        deps.set_property("libmcfp", "cmake_file_name", "mcfp")
        deps.set_property("libmcfp", "cmake_target_name", "mcfp::mcfp")
        deps.generate()

        tc = CMakeToolchain(self)
        # cif-tools' own CMakeLists sets CMAKE_CXX_STANDARD 17, but the
        # published libcifpp/10.0.4 headers require C++20 (remove_cvref_t /
        # constrained template FloatType in item.hpp) and the sources use
        # std::format. Pushing `-std=c++20` onto the C++ flags wins over the
        # CMakeLists' plain set(CMAKE_CXX_STANDARD 17): CMake only appends its
        # own -std= flag when the flags don't already carry one.
        # Note: C++ only — do NOT add to extra_cflags (C rejects -std=c++20).
        flags = tc.extra_cxxflags
        if "-std=c++20" not in flags:
            flags.append("-std=c++20")
        # libc++15 (OHOS SDK) ships std::format behind -fexperimental-library
        # (probe-verified: -std=c++20 alone fails, adding the flag compiles).
        if "-fexperimental-library" not in flags:
            flags.append("-fexperimental-library")
        tc.generate()

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Patches declared in conandata.yml must be applied explicitly — without
        # this call they are exported but never used, which silently leaves
        # CMakeLists.txt at C++17 (measured: CXX_FLAGS ended with -std=c++17).
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream test suite is disabled in the 2.0.0 release
        # (CMakeLists.txt: the entire ``if(BUILD_TESTING)`` block is
        # commented out) — there are no upstream tests to run.

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # man pages installed under share/man — keep them (installed by
        # upstream `install(FILES doc/*.1 DESTINATION share/man/man1)`).

    def package_info(self):
        # tool package: only executables
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
