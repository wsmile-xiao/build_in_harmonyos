#!/usr/bin/env python3
"""Consumer tests for libsass 3.6.6."""

import glob
import os
import shlex
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibsassTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        sysroot = self._sysroot(executables)
        if sysroot:
            toolchain.variables["CMAKE_SYSROOT"] = str(sysroot)
        toolchain.generate()
        VirtualRunEnv(self).generate()

    def _sysroot(self, executables):
        sysroot = self.conf.get("tools.build:sysroot", default=None)
        if str(self.settings.os) != "OHOS":
            return sysroot

        if sysroot:
            configured = os.path.normpath(str(sysroot)).replace("\\", "/")
            if os.path.isfile(os.path.join(configured, "usr", "include", "features.h")):
                return configured

        compiler = executables.get("cpp") or executables.get("c")
        if not compiler:
            return sysroot

        compiler_dir = os.path.dirname(str(compiler))
        candidates = [os.path.join(compiler_dir, "..", "..", "sysroot")]
        sdk_parent = os.path.normpath(os.path.join(compiler_dir, ".."))
        for pattern in (
            os.path.join(sdk_parent, "ohos-sdk.org", "*", "ohos", "native", "sysroot"),
            os.path.join(sdk_parent, "ohos-sdk", "*", "ohos", "native", "sysroot"),
        ):
            candidates.extend(sorted(glob.glob(pattern)))

        for candidate in candidates:
            candidate = os.path.normpath(candidate).replace("\\", "/")
            if os.path.isfile(os.path.join(candidate, "usr", "include", "features.h")):
                return candidate
        return sysroot or os.path.normpath(candidates[0]).replace("\\", "/")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built libsass consumer cannot run on this host.")
            return
        executable = os.path.join(self.build_folder, "libsass_consumer")
        if os.name == "nt":
            executable += ".exe"
        self.run(self._shell_join([executable]), cwd=self.build_folder, env="conanrun")

    @staticmethod
    def _shell_join(arguments):
        arguments = [str(argument) for argument in arguments]
        if os.name == "nt":
            return subprocess.list2cmdline(arguments)
        return shlex.join(arguments)
