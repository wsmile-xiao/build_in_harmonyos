#!/usr/bin/env python3
"""C consumer test for the Berkeley DB C API."""

import os
import re

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class DbCTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _native_compiler(self, tool):
        """Resolve a Windows-hosted POSIX wrapper to its native SDK compiler."""
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        configured = executables.get(tool)
        if not configured:
            return None
        configured = os.fspath(configured).replace("\\", "/")
        if not configured.lower().endswith(".sh"):
            return configured
        try:
            content = open(configured, encoding="utf-8").read()
        except OSError:
            return configured
        for candidate in re.findall(r'exec\s+"([^"]+\.exe)"', content):
            if tool == "c" and candidate.lower().endswith("/clang.exe"):
                return candidate
            if tool in ("cpp", "cxx") and candidate.lower().endswith("/clang++.exe"):
                return candidate
        return configured

    def _native_flags(self, tool="c"):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        configured = executables.get(tool)
        if not configured:
            return []
        configured = os.fspath(configured).replace("\\", "/")
        try:
            content = open(configured, encoding="utf-8").read()
        except OSError:
            return []
        flags = []
        target = re.search(r"--target[= ]([^\s]+)", content)
        sysroot = re.search(r'--sysroot="([^"]+)"', content)
        if target:
            flags.append("--target=%s" % target.group(1))
        if sysroot:
            escaped_sysroot = sysroot.group(1).replace('"', '\\"')
            flags.append('--sysroot=\\"%s\\"' % escaped_sysroot)
        if "-no-pie" in content:
            flags.append("-no-pie")
        if "-D__MUSL__" in content:
            flags.append("-D__MUSL__")
        if target:
            flags.append("-fuse-ld=lld")
        return flags

    def generate(self):
        tc = CMakeToolchain(self)
        settings_build = getattr(self, "settings_build", self.settings)
        if str(self.settings.os) == "OHOS" and str(settings_build.os) == "Windows":
            compiler = self._native_compiler("c")
            compiler_cpp = self._native_compiler("cpp") or self._native_compiler("cxx")
            if compiler:
                tc.variables["CMAKE_C_COMPILER"] = compiler
            if compiler_cpp:
                tc.variables["CMAKE_CXX_COMPILER"] = compiler_cpp
            flags = self._native_flags("c")
            if flags:
                joined_flags = " ".join(flags)
                tc.variables["CMAKE_C_FLAGS"] = joined_flags
                tc.variables["CMAKE_EXE_LINKER_FLAGS"] = joined_flags
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built db-c consumer cannot run on this host.")
            return
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_package"), env="conanrun")
