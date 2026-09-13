#!/usr/bin/env python3
"""Conan test_package — bctoolbox 5.3.115 (real consumer smoke test)

Builds two consumer programs against the packaged library and executes them:
  - test_bctoolbox      (C):   bctbx_list + logging handler round-trip
  - test_bctoolbox_cpp  (C++): bctbx_is_matching_regex + BctbxException
"""
import os

from conan import ConanFile
from conan.tools.cmake import cmake_layout


class BctoolboxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # Keep built test binaries in the build folder (not the package source dir).
        cmake_layout(self)

    def test(self):
        info = self.dependencies["bctoolbox"].cpp_info
        # Take compiler executables from the profile conf (dict first; point-key
        # access raises ConanException on Conan 2.29).
        compilers = self.conf.get("tools.build:compiler_executables") or {}
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")

        includedirs = " ".join("-I" + d for d in info.includedirs)
        libdirs = " ".join("-L" + d for d in info.libdirs)
        libs = " ".join("-l" + l for l in info.libs)
        syslibs = " ".join("-l" + l for l in info.system_libs)
        builddir = os.path.join(self.build_folder, "bin")
        os.makedirs(builddir, exist_ok=True)

        c_src = os.path.join(self.source_folder, "test_bctoolbox.c")
        cxx_src = os.path.join(self.source_folder, "test_bctoolbox_cpp.cpp")

        c_bin = os.path.join(builddir, "test_bctoolbox")
        cxx_bin = os.path.join(builddir, "test_bctoolbox_cpp")

        self.run(f"{cc} {c_src} -o {c_bin} {includedirs} {libdirs} {libs} {syslibs}")
        self.run(f"{cxx} {cxx_src} -o {cxx_bin} -std=c++17 {includedirs} {libdirs} {libs} {syslibs}")

        self.run(f'"{c_bin}"', env="conanrun")
        self.run(f'"{cxx_bin}"', env="conanrun")
