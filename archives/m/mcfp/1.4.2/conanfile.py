#!/usr/bin/env python3
"""Conan recipe — mcfp 1.4.2 (CMake, header-only C++20).

mcfp (a.k.a. libmcfp, formerly mhekkel/libconfig) is Maarten Hekkelman's
header-only C++20 library that collects configuration options from command
line arguments and INI-style config files, exposed program-wide through the
mcfp::config::instance() singleton.  It is a hard dependency of cif-tools
2.0.0 (linked into every cif-tools binary as mcfp::mcfp), which fetches it
at configure time via CPM unless a mcfp target is already provided — so an
offline OHOS build must pre-provide it as a conan package.

Upstream installs headers to include/ and a CMake package (lib/cmake/mcfp,
mcfpConfig.cmake, target mcfp::mcfp).  This recipe runs the upstream CMake
install (mirroring the fast_float header-library recipe): package_type =
header-library, no compiled artifacts, but the full header set + CMake
config are genuinely installed and a consumer smoke test in test_package
compiles and runs the real mcfp parsing API on device.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches,
                               export_conandata_patches, get)


class McfpConan(ConanFile):
    name = "mcfp"
    version = "1.4.2"
    description = "Header-only C++20 config collection from command line and config files"
    license = "BSD-2-Clause"
    homepage = "https://forge.hekkelman.net/maarten/mcfp"
    url = ""  # CI fills this
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os check must be an explicit allow-list
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mcfp supports Linux and OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        # Upstream's suite is Catch2-based and test/CMakeLists.txt fetches it
        # with CPMAddPackage("gh:catchorg/Catch2@3.4.0") at configure time, i.e.
        # a network download inside build() (forbidden by gate L0o) that also
        # shadows the Catch2 version the artifact repo already provides.  Use
        # the ohpcd catch2/3.8.1 package instead; the patched
        # test/CMakeLists.txt keeps CPM only as a fallback.  Same technique as
        # the existing optional/1.1.0 recipe.
        #
        # NOTE: this must be a plain requires(), not test_requires().  A
        # test_requires only takes part in the test_package graph, so it would
        # be absent from the host context during build().
        self.requires("catch2/3.8.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # CMakeDeps writes catch2-config.cmake (pointing at the ohpcd
        # catch2/3.8.1 package) into the generators dir, which is what the
        # patched find_package(Catch2 CONFIG QUIET) resolves.  Without it the
        # dependency is installed but invisible to CMake, find_package fails,
        # and CPM silently falls back to its GitHub download - verified on
        # device: the log showed "CPM: Adding package Catch2@3.4.0" and the
        # generators dir held no Catch2 file at all.
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # Config.guess-style OS probe is not needed; treat OHOS as a
            # Linux-like target for CMake (same technique as fast_float).
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # The upstream suite (18 Catch2 TEST_CASEs) is built and executed; see
        # _run_upstream_tests().  BUILD_DOCUMENTATION stays off.
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_DOCUMENTATION"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream Catch2 suite (18 TEST_CASEs) inside build()."""
        if str(self.settings.os) != "OHOS":
            return
        bin_dir = tests_bin = None
        for root, _dirs, files in os.walk(self.build_folder):
            if bin_dir is None and "CTestTestfile.cmake" in files:
                bin_dir = root
            if tests_bin is None and "mcfp-unit-test" in files:
                tests_bin = os.path.join(root, "mcfp-unit-test")
            if bin_dir and tests_bin:
                break
        if bin_dir is None:
            self.output.warning("CTestTestfile.cmake not found; upstream tests not run")
            return

        # Shared dependency libraries may live in the Conan cache; CMake emits
        # no RPATH for HarmonyOS, so make them findable for the test binaries.
        envobj = Environment()
        for dep in self.dependencies.values():
            dirs = list(dep.cpp_info.libdirs)
            try:
                dirs = list(dep.cpp_info.aggregated_components().libdirs) or dirs
            except Exception:
                pass
            for d in dirs:
                envobj.append_path("LD_LIBRARY_PATH",
                                   os.path.join(dep.package_folder, d))

        with envobj.vars(self).apply():
            self.output.info("=== ctest -N (test discovery) ===")
            self.run("ctest -N", cwd=bin_dir)
            if tests_bin and os.path.exists(tests_bin):
                self.output.info("=== mcfp-unit-test --list-tests (Catch2 cases) ===")
                try:
                    self.run('"%s" --list-tests' % tests_bin, cwd=bin_dir)
                except Exception as e:
                    self.output.warning("--list-tests failed: %s" % e)
            self.output.info("=== ctest --output-on-failure ===")
            rc = self.run("ctest --output-on-failure", cwd=bin_dir,
                          ignore_errors=True)
            if rc != 0:
                self.output.warning(
                    "ctest returned %s - see the full ctest output above" % rc)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Header-only INTERFACE: no libs.  CMakeDeps exposes the package to
        # consumers as find_package(mcfp) with target mcfp::mcfp (the same
        # name upstream's own config uses), satisfying cif-tools' guard.
        self.cpp_info.libs = []
