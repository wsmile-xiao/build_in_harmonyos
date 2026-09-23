#!/usr/bin/env python3
"""Conan recipe — stats 3.4.0 (header-only C++ statistics library).

StatsLib upstream (kthohr/stats) ships no build system: the deliverable is
the headers in include/ (stats.hpp + stats_incl/). Its only dependency is
GCEM (header-only constexpr math, included by stats.hpp via
#include "gcem.hpp").

Upstream tests live in tests/{dens,prob,quant,rand} as 84 standalone .cpp
programs (one executable each). The recipe compiles and runs all 84 in
build() through a generated CMake driver, so `conan create` on a clean
machine reproduces the documented upstream flow
(tests/setup; ./configure; make; run each *.test).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save


class StatsConan(ConanFile):
    name = "stats"
    version = "3.4.0"
    description = "StatsLib: a C++ header-only library of probability distribution functions"
    license = "Apache-2.0"
    homepage = "https://github.com/kthohr/stats"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # stats.hpp: #include "gcem.hpp" — GCEM is the only upstream dependency
        # (upstream README: "The only dependency is the latest version of GCEM").
        self.requires("gcem/1.18.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        tests_dir = os.path.join(self.source_folder, "tests")
        suites = ("dens", "prob", "quant", "rand")
        entries = []
        for suite in suites:
            suite_dir = os.path.join(tests_dir, suite)
            for fname in sorted(os.listdir(suite_dir)):
                if fname.endswith(".cpp"):
                    entries.append(
                        (suite, fname[:-4], os.path.abspath(os.path.join(suite_dir, fname)))
                    )

        gcem = self.dependencies["gcem"]
        gcem_include = os.path.join(gcem.package_folder, gcem.cpp_info.includedirs[0])
        stats_include = os.path.join(self.source_folder, "include")

        lines = [
            "cmake_minimum_required(VERSION 3.15)",
            "project(stats_upstream_tests CXX)",
            "set(CMAKE_CXX_STANDARD 11)",
            "set(CMAKE_CXX_STANDARD_REQUIRED ON)",
            "add_compile_definitions(STATS_ENABLE_STDVEC_WRAPPERS)",
        ]
        for suite, target, src in entries:
            lines.append(f"add_executable({suite}__{target} {src})")
            lines.append(
                f"target_include_directories({suite}__{target} PRIVATE "
                f'"{stats_include}" "{gcem_include}")'
            )
        driver_dir = os.path.join(self.build_folder, "upstream-tests")
        save(self, os.path.join(driver_dir, "CMakeLists.txt"), "\n".join(lines) + "\n")

        cmake = CMake(self)
        cmake.configure(build_script_folder=driver_dir)
        cmake.build()

        # Each upstream program throws on failure (uncaught std::runtime_error
        # from print_test_fail) and returns 0 only when every check passes.
        expected = 84
        if len(entries) != expected:
            raise RuntimeError(
                "Expected %d upstream test programs, found %d" % (expected, len(entries))
            )
        for index, (suite, target, _) in enumerate(entries, 1):
            self.output.info(
                "STATS_UPSTREAM_TEST[%d/%d]=%s/%s" % (index, expected, suite, target)
            )
            exe = os.path.join(self.build_folder, f"{suite}__{target}")
            self.run('"%s"' % exe, env="conanrun")

    def package(self):
        inc_src = os.path.join(self.source_folder, "include")
        for pattern in ("*.hpp", "*.ipp"):
            copy(
                self,
                pattern,
                src=inc_src,
                dst=os.path.join(self.package_folder, "include"),
                keep_path=True,
            )

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
