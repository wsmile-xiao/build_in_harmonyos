#!/usr/bin/env python3
"""Conan recipe — libmcfp 2.1.1 (CMake, compiled library).

libmcfp (github.com/mhekkel/libmcfp, BSD-2-Clause) is Maarten Hekkelman's
C++23 configuration-collection library: it gathers configuration options from
command-line arguments and INI-style config files, exposed program-wide
through the mcfp::config::instance() singleton.

Upstream 2.1.1 is a *compiled* library (src/*.cpp: mcfp.cpp, options.cpp,
text.cpp, charconv-fast_float.cpp) plus an optional C++20 module library
(mcfp-module), CMake >= 3.28, C++23.  When the toolchain lacks floating-point
std::from_chars (true on the OHOS libc++), the upstream CMakeLists falls back
to CPMFetching fast_float from github.com at configure time; this recipe
pre-installs fast_float/8.0.1 (patch 0001) and catch2/3.8.1 for the upstream
Catch2 suite (patch 0002), both already published on the ohpcd registry.
The OHOS build treats CMake as a Linux-like target (CMAKE_SYSTEM_NAME=Linux,
same technique as fast_float / mcfp 1.4.2).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches,
                               export_conandata_patches, get)


class LibmcfpConan(ConanFile):
    name = "libmcfp"
    version = "2.1.1"
    description = "C++23 config collection from command line and INI config files"
    license = "BSD-2-Clause"
    homepage = "https://github.com/mhekkel/libmcfp"
    url = ""  # CI fills this
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os check must be an explicit allow-list
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libmcfp supports Linux and OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        # fast_float: needed whenever the toolchain lacks floating-point
        # std::from_chars (OHOS libc++ deletes the float/double overloads).
        # catch2: the upstream Catch2 suite; patched test/CMakeLists.txt keeps
        # CPM only as a fallback.  Both must be plain requires() (host context
        # during build(), not just test_package graph).
        self.requires("fast_float/8.0.1")
        self.requires("catch2/3.8.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # Treat OHOS as a Linux-like target for CMake (same technique as
            # fast_float / mcfp 1.4.2).
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # The upstream Catch2 suite (37 TEST_CASEs) is built and executed; see
        # _run_upstream_tests().  The optional C++20 module library (clang 15
        # module support is experimental) and docs stay off.
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_DOCUMENTATION"] = "OFF"
        tc.variables["MCFP_BUILD_CXX_MODULE"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream Catch2 suite (unit-test.cpp 35 + lib-test.cpp 2
        TEST_CASEs = 37) inside build(), on the OHOS device."""
        if str(self.settings.os) != "OHOS":
            return
        bin_dir = tests_dir = None
        for root, _dirs, files in os.walk(self.build_folder):
            if bin_dir is None and "CTestTestfile.cmake" in files:
                bin_dir = root
            if tests_dir is None and "unit-test-app" in files:
                tests_dir = root
            if bin_dir and tests_dir:
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
            for exe in ("unit-test-app", "lib-test-app"):
                p = os.path.join(tests_dir, exe)
                if os.path.exists(p):
                    self.output.info(f"=== {exe} --list-tests (Catch2 cases) ===")
                    try:
                        self.run('"%s" --list-tests' % p, cwd=bin_dir)
                    except Exception as e:
                        self.output.warning("--list-tests failed: %s" % e)
            self.output.info("=== ctest --output-on-failure ===")
            # Upstream suite is a real quality gate: a failing ctest must fail
            # the build (W3/CI honesty), not degrade to a warning.
            rc = self.run("ctest --output-on-failure", cwd=bin_dir,
                          ignore_errors=True)
            self.output.info("=== mcfp-unit-test exit code: %s ===" % rc)
            if rc != 0:
                raise ConanException(
                    "Upstream Catch2 suite failed with ctest exit code %s - "
                    "see full ctest output above" % rc)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The upstream library target is mcfp (libmcfp.a/.so).
        self.cpp_info.libs = ["mcfp"]
