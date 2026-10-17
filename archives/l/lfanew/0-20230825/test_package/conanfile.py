#!/usr/bin/env python3
"""Conan test_package for lfanew — HarmonyOS PC consumer test (R34 / rule12).

Builds test_lfanew.c against the packaged libfanew.a + headers, then runs it
with the packaged `lfanew` executable. The consumer creates MZ images with
the package headers, drives the CLI in all three modes plus refusal paths,
parses the produced files back, and scans the work directory with the
libc scandir() declared by <lfanew/dirent.h> and copies each entry with the
package's _direntdup() (patched code path).

Both the consumer and the packaged CLI are static AArch64 ELF: on an AArch64
runner they run directly, on an x86_64 runner through qemu-aarch64 (E544).
Neither available -> the test fails instead of silently skipping.
"""
import os
import platform
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class LfanewTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _launcher(self):
        if platform.machine().lower() in ("aarch64", "arm64"):
            return ""
        qemu = shutil.which("qemu-aarch64")
        if not qemu:
            raise ConanException(
                "lfanew test needs an AArch64 runner or qemu-aarch64 "
                f"(machine={platform.machine()})")
        return qemu

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        tool = os.path.join(dep.package_folder, "bin", "lfanew")
        if not os.path.isfile(tool):
            raise ConanException(f"packaged lfanew executable missing: {tool}")
        probe = os.path.join(self.cpp.build.bindir, "test_lfanew")
        workdir = os.path.join(self.build_folder, "lfanew-work")
        shutil.rmtree(workdir, ignore_errors=True)
        os.makedirs(workdir)
        launcher = self._launcher()
        prefix = f'"{launcher}" ' if launcher else ""
        self.run(f'{prefix}"{probe}" "{tool}" "{workdir}" "{launcher}"',
                 env="conanrun")
