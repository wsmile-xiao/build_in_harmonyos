#!/usr/bin/env python3
"""Conan recipe — clue 1.0.0 (header-only C++03 logging library).

clue is a tiny header-only C++ logging framework by Martin Moene
(single header ``include/clue.hpp``, no dependencies). Upstream ships
no CMakeLists.txt, only ``tests/Makefile`` whose default ``all`` target
compiles the lest test suite and runs the resulting binary in one shot.

This recipe:
- packages the single header + BSL-1.0 license text,
- runs the real upstream tests during ``build()`` via the upstream
  Makefile (C++ compiler comes from the conan profile through
  ``conanbuild``; the Makefile's own ``CXXFLAGS`` assignment
  ``-Wall -Wextra -Weffc++ -std=c++03 -I../include`` stays in force
  because makefile assignments override environment variables).
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain


class ClueConan(ConanFile):
    name = "clue"
    version = "1.0.0"
    description = (
        "clue is a C++03 header-only library to log messages with a "
        "severity and optional module identifier."
    )
    license = "BSL-1.0"
    homepage = "https://github.com/martinmoene/clue"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("logging", "header-only", "cpp03")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Source is used in place (tests/Makefile relies on the relative
        # path ../include); compile artifacts land in a private build dir.
        self.folders.source = "."
        self.folders.build = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Provides the conanbuild env (CC/CXX from the profile's
        # tools.build:compiler_executables) for the upstream Makefile.
        AutotoolsToolchain(self).generate()

    def build(self):
        # No conandata patches for now; keep the canonical hook so any
        # future patch set is applied before the upstream build runs.
        apply_conandata_patches(self)
        # Upstream tests/Makefile target `all`:
        #   $(CXX) $(CXXFLAGS) -o test_clue test_clue.cpp test_clue_part2.cpp
        #   ./test_clue
        # so the real upstream test suite is compiled AND executed here.
        self.run("make -j2 -C tests", cwd=self.source_folder, env="conanbuild")

    def package(self):
        copy(self, "clue.hpp",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE_1_0.txt",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "clue")
        self.cpp_info.set_property("cmake_target_name", "clue::clue")
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
