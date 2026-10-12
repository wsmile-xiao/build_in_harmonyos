#!/usr/bin/env python3
"""Installed-package consumer tests for routino 3.4.3.

Builds test_routino against the packaged libroutino and runs it. The
binary calls real public APIs (no stubs) and prints
HMBS_TEST_PACKAGE_RESULT itself; the marker flows through self.run()
into the conan log.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class RoutinoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "test_routino.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _resolve_compiler(self, kind):
        # Profile pins /data/service/hnp/bin/clang which is absent on the
        # preflight worker (CMake error: CMAKE_C_COMPILER ... could not be
        # found); fall back to PATH discovery like the main recipe.
        try:
            conf = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        except Exception:
            conf = {}
        key = "c" if kind == "c" else ("cpp" if "cpp" in conf else "cxx")
        configured = conf.get(key)
        if configured:
            if os.path.isabs(configured):
                if os.path.isfile(configured) and os.access(configured, os.X_OK):
                    return configured
            else:
                found = shutil.which(configured.split()[0])
                if found:
                    return found
                return configured
        default = "clang" if kind == "c" else "clang++"
        return shutil.which(default) or default

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        cc = self._resolve_compiler("c")
        cxx = self._resolve_compiler("cpp")
        self.output.info("routino test_package compilers: CC=%s CXX=%s" % (cc, cxx))
        tc.variables["CMAKE_C_COMPILER"] = cc
        tc.variables["CMAKE_CXX_COMPILER"] = cxx
        tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        tc.generate()

    def build(self):
        os.environ["CC"] = self._resolve_compiler("c")
        os.environ["CXX"] = self._resolve_compiler("cpp")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _shell(self):
        for cand in (os.environ.get("CONFIG_SHELL"), os.environ.get("SHELL")):
            if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        for name in ("bash", "sh"):
            found = shutil.which(name)
            if found:
                return found
        return "/bin/sh"

    def test(self):
        if can_run(self):
            binary = os.path.join(self.cpp.build.bindir, "test_routino")
            # Run via shell (zlib precedent: direct exec is fragile
            # under the OHOS shell environment). Never trust a stale
            # absolute CONFIG_SHELL; fall back to an existing shell.
            bash = self._shell()
            self.run(f"{bash} -c '{binary}'", env="conanrun")
        else:
            self.output.info("cross-building: compile+link check only")
