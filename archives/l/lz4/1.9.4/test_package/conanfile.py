#!/usr/bin/env python3
"""Conan test_package — lz4 1.9.4 L1 consumer test.

R34: test calls lz4 API (LZ4_compress_default / LZ4_decompress_safe).

NOTE: OHOS /bin/sh is restricted and CMake always shells out to /bin/sh,
so we avoid CMake here and compile/link directly with clang (following the
zstd test_package approach). We also run the probe through an available bash.
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class Lz4TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["lz4"].cpp_info
        # Include the dependency headers
        incs = ["-I" + p for p in dep.includedirs]
        inc = " ".join(incs)
        libdir = dep.libdirs[0]
        cc = os.environ.get("CC", "clang")
        # Link against the static lib (default build) then run
        self.run(f"{cc} test.c -o test_lz4 {inc} -L{libdir} -llz4")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile + link only")
            return
        # OHOS /bin/sh restricted → run through bash
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c 'cd \"{os.getcwd()}\" && ./test_lz4'", env="conanrun")
