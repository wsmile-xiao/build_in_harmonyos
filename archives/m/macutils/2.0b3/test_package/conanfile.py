#!/usr/bin/env python3
"""Conan test_package for macutils 2.0b3.

macutils only ships command-line tools, so the consumer is a C program built
with the target toolchain (test_macutils.c) that drives the packaged tools
and verifies their output with independent format implementations:

1. macunpack extracts a PackIt archive synthesised by the consumer (Mac Roman
   name mapping, type/creator, forks byte-identical, CRC-corrupted archive
   rejected);
2. binhex output is decoded by an independent BinHex 4.0 decoder (RLE,
   header/data/resource CRCs);
3. hexbin restores the data fork byte-for-byte and rejects a tampered .hqx;
4. macstream -> macsave MacBinary round trip is byte-identical.
"""
import os
import platform
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout

TOOLS = ("macunpack", "hexbin", "binhex", "macsave", "macstream", "tomac", "frommac")


class MacutilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindir = os.path.join(self.dependencies["macutils"].package_folder, "bin")
        for tool in TOOLS:
            if not os.path.isfile(os.path.join(bindir, tool)):
                raise RuntimeError(f"macutils package is missing bin/{tool}")
        if not can_run(self):
            return
        if str(self.settings.arch) == "armv8" and platform.machine() not in ("aarch64", "arm64"):
            # Dynamically linked OHOS binaries need /lib/ld-musl-aarch64.so.1,
            # which an x86_64 runner does not have; the AArch64 CI worker runs it.
            self.output.warning("Skipping target execution on a non-AArch64 build machine")
            return
        consumer = os.path.join(self.cpp.build.bindir, "test_macutils")
        workdir = os.path.join(self.build_folder, "macutils-consumer")
        shutil.rmtree(workdir, ignore_errors=True)
        # conanrun puts the macutils bin/ directory on PATH for execvp().
        self.run(f'"{consumer}" "{workdir}"', env="conanrun")
