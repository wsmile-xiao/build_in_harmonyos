#!/usr/bin/env python3
"""Conan recipe for chuffed 0.13.1 — CMake static library + fzn-chuffed solver binary.

Chuffed is a constraint programming (CP) solver implementing lazy clause
generation (LCG). This recipe builds:

  - libchuffed.a      core solver engine (static)
  - libchuffed_fzn.a  FlatZinc frontend library (static)
  - fzn-chuffed       FlatZinc solver executable

Upstream options are fixed for the OHOS target:
  - CP_PROFILER=OFF      (optional CP Profiler integration, not available)
  - SUPPORT_VAR_IMPACT=OFF (optional impact branching, upstream default)
  - STATIC=OFF           (never pass -static to the linker)

Bison/flex are required at build time to regenerate the FlatZinc parser.
Upstream ships a cached generated_parser/ as fallback; the recipe relies on
the cached parser so no bison/flex tool_requires is needed.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class ChuffedConan(ConanFile):
    name = "chuffed"
    version = "0.13.1"
    description = "Chuffed, a lazy clause generation constraint programming solver"
    topics = ("constraint-programming", "solver", "cp", "lazy-clause-generation", "flatzinc")
    homepage = "https://github.com/chuffed/chuffed"
    url = "https://github.com/chuffed/chuffed"
    license = "MIT"
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanException("chuffed is supported only on Linux/OHOS in this recipe")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanException("OHOS builds require armv8/aarch64")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream CMake options: keep the optional integrations OFF so the
        # build is dependency-free (no CP Profiler, no var impact sources).
        tc.variables["CP_PROFILER"] = False
        tc.variables["SUPPORT_VAR_IMPACT"] = False
        tc.variables["STATIC"] = False
        # ZLIB is only needed for 3 of the 25 examples (EXCLUDE_FROM_ALL);
        # examples are not part of the install set, keep the recipe ZLIB-free.
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_ZLIB"] = True
        # R26-compatible: the upstream target is a plain static lib.
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # Upstream installs an exported CMake config: chuffed-config.cmake
        # with imported targets `chuffed` and `chuffed_fzn` (package namespaced
        # via Conan: chuffed::chuffed / chuffed::chuffed_fzn).
        self.cpp_info.set_property("cmake_file_name", "chuffed")
        self.cpp_info.set_property("cmake_target_name", "chuffed::chuffed")
        self.cpp_info.set_property("cmake_target_aliases", ["chuffed::chuffed_fzn"])
        self.cpp_info.libs = ["chuffed_fzn", "chuffed"]
        if str(self.settings.os) in ("Linux", "OHOS", "FreeBSD"):
            self.cpp_info.system_libs.append("pthread")
