#!/usr/bin/env python3
"""Installed-package consumer tests for leatherman 1.12.1.

Builds test_leatherman against the packaged components
(util/locale/logging/json_container/file_util) and runs it. The binary
calls real public APIs (no stubs) and prints HMBS_TEST_PACKAGE_RESULT
itself; the marker flows through self.run() into the conan log.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LeathermanTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "test_leatherman.cpp"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        _c = self._resolve_cmake_compiler("c", ("clang", "cc"), "CC")
        _cxx = self._resolve_cmake_compiler("cpp", ("clang++", "c++"), "CXX")
        if _c:
            tc.cache_variables["CMAKE_C_COMPILER"] = _c
        if _cxx:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = _cxx
        self.output.info("test_package cmake compilers c=%s cxx=%s" % (_c, _cxx))
        tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        tc.generate()
        self._fix_generated_toolchain(_c, _cxx)

    def _resolve_cmake_compiler(self, key, fallback_names, env_name):
        try:
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
        except Exception:
            executables = {}
        if not isinstance(executables, dict):
            executables = {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        for name in fallback_names:
            found = shutil.which(name)
            if found and os.path.isfile(found):
                return found
        env_hit = os.environ.get(env_name, "")
        if env_hit and os.path.isfile(env_hit):
            return env_hit
        return configured or None

    def _fix_generated_toolchain(self, c, cxx):
        try:
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
        except Exception:
            executables = {}
        if not isinstance(executables, dict):
            executables = {}
        pairs = []
        for key, resolved in (("c", c), ("cpp", cxx)):
            old = executables.get(key)
            if (old and resolved and old != resolved
                    and not os.path.exists(old) and os.path.exists(resolved)):
                pairs.append((old, resolved))
        if not pairs:
            return
        path = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        try:
            if not os.path.isfile(path):
                self.output.warning(
                    "cmake toolchain file not found: %s" % path)
                return
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            orig = text
            for old_p, new_p in pairs:
                text = text.replace(old_p, new_p)
            if text != orig:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
                self.output.info(
                    "fixed stale compiler path in %s" % path)
            for line in text.splitlines():
                s = line.strip()
                if "CMAKE_C_COMPILER" in s or "CMAKE_CXX_COMPILER" in s:
                    self.output.info("toolchain %s" % s)
        except Exception as exc:
            self.output.warning("toolchain compiler fix failed: %s" % exc)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            binary = os.path.join(self.cpp.build.bindir, "test_leatherman")
            self.run(binary, env="conanrun")
        else:
            self.output.info("cross-building: compile+link check only")
