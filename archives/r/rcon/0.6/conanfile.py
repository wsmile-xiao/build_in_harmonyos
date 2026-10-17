#!/usr/bin/env python3
"""Conan recipe for rcon 0.6 — Source RCON client for the command line.

n0la/rcon implements the Valve Source RCON protocol as a CLI tool.
Build: CMake (>= 3.5), links glib-2.0 via pkg-config.
Upstream tests: tests/srcrcontest.c (1 ctest entry) links the check framework.

OHOS adaptation:
- srcrcon.c ships a portable fallback for arc4random_uniform() based on
  arc4random() (musl >= 1.2.4 provides it), so the upstream hard dependency
  on libbsd (REQUIRED when the C library lacks arc4random_uniform) is dropped.
- CMake minimum version bumped 3.1/3.0 -> 3.5 (CMake >= 4 removed < 3.5 compat).
"""
import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps


class RconConan(ConanFile):
    name = "rcon"
    version = "0.6"
    description = "Source RCON client for the command line (Valve Source RCON protocol)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/n0la/rcon"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # CMakeLists.txt: PKG_CHECK_MODULES(GLIB2 REQUIRED glib-2.0)
        self.requires("glib/2.84.0.1")

    def build_requirements(self):
        # tests/CMakeLists.txt: PKG_CHECK_MODULES(CHECK REQUIRED check)
        # (host-context test-only dependency so its .pc reaches pkg_check_modules)
        self.test_requires("check/0.15.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Expose glib-2.0.pc / check.pc (and their transitive deps) to
        # pkg_check_modules during configure.
        PkgConfigDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def _test_dependency(self, name):
        """Resolve a (test) requirement for runtime flags, mirroring the
        merged rgxg/0.1.2 recipe."""
        for group in (self.dependencies.test, self.dependencies.host,
                      self.dependencies.build):
            try:
                return group[name]
            except KeyError:
                continue
        raise ConanException(f"missing test dependency: {name}")

    def _check_run_prefix(self):
        """Inline env assignments for running the check-based upstream test.

        Mirror of the merged rgxg/0.1.2 recipe: on OHOS, the conanbuild env
        does not put the test-only check library on LD_LIBRARY_PATH (glib is
        a host require and resolves fine, check is test-only and does not),
        the target /tmp is read-only (Check 0.15.2 consults TEMP/TMP/TMPDIR
        before P_tmpdir), and Check's forked runner trips over HMDFS
        permission normalisation (run in-process with CK_FORK=no instead).
        """
        variables = {}
        if str(self.settings.os) == "OHOS":
            check = self._test_dependency("check")
            libdir = os.path.join(
                check.package_folder, (check.cpp_info.libdirs or ["lib"])[0])
            if os.path.isdir(libdir):
                variables["LD_LIBRARY_PATH"] = libdir
            test_tmp = os.path.join(self.build_folder, "check-tmp")
            os.makedirs(test_tmp, exist_ok=True)
            variables["TEMP"] = test_tmp
            variables["TMP"] = test_tmp
            variables["TMPDIR"] = test_tmp
            variables["CK_FORK"] = "no"
        return " ".join(f"{key}={shlex.quote(val)}" for key, val in variables.items())

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream test: 1 ctest entry (srcrcontest).
        if can_run(self):
            self.run(f"{self._check_run_prefix()} ctest --output-on-failure",
                     cwd=self.build_folder, env="conanbuild")
        else:
            self.output.info("cross-compiling: upstream ctest compiled but not executed")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
