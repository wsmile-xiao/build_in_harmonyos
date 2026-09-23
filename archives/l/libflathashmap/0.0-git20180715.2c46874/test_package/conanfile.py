#!/usr/bin/env python3
"""Conan consumer tests — libflathashmap on OHOS/aarch64."""

import os
import platform
import shlex
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibflathashmapTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        toolchain.variables["CMAKE_CXX_STANDARD"] = "14"
        toolchain.variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        toolchain.variables["CMAKE_CXX_EXTENSIONS"] = False
        toolchain.variables["LIBFLATHASHMAP_TARGET_OS"] = str(self.settings.os)
        toolchain.variables["LIBFLATHASHMAP_TARGET_ARCH"] = str(self.settings.arch)
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        bindir = self.cpp.build.bindirs[0]
        for executable in (
            "test_flat_hash_map",
            "test_bytell_hash_map",
            "test_unordered_map",
            "test_ohos",
        ):
            self.run(self._test_command(os.path.join(bindir, executable)), env="conanrun")

    def _test_command(self, executable):
        command = shlex.quote(executable)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp")
        runtime_lib = None
        if cxx:
            candidate = Path(cxx).resolve().parents[1] / "lib/aarch64-linux-ohos"
            if (candidate / "libc++_shared.so").is_file():
                runtime_lib = candidate
        if self._requires_emulation():
            qemu = shutil.which("qemu-aarch64")
            if not qemu:
                raise ConanInvalidConfiguration(
                    "qemu-aarch64 is required for cross-built consumer tests"
                )
            qemu_root = os.environ.get("QEMU_LD_PREFIX")
            if not qemu_root or not (Path(qemu_root) / "lib/ld-musl-aarch64.so.1").is_file():
                raise ConanInvalidConfiguration(
                    "QEMU_LD_PREFIX must name an aarch64 musl runtime root"
                )
            if runtime_lib is None:
                raise ConanInvalidConfiguration(
                    "The OHOS compiler path must resolve to its aarch64 libc++ runtime"
                )
            command = "{} -L {} -E {} {}".format(
                shlex.quote(qemu),
                shlex.quote(qemu_root),
                shlex.quote(f"LD_LIBRARY_PATH={runtime_lib}"),
                command,
            )
        elif runtime_lib is not None:
            command = "env {} {}".format(
                shlex.quote(f"LD_LIBRARY_PATH={runtime_lib}"), command
            )
        return command

    def _requires_emulation(self):
        if cross_building(self):
            return True
        native_arch = platform.machine().lower()
        return str(self.settings.os) == "OHOS" and (
            platform.system() != "HarmonyOS"
            or native_arch not in ("aarch64", "arm64")
        )
