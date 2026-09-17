#!/usr/bin/env python3
"""Conan test_package — lz4 1.10.0.3 L1 test.

R34: test calls lz4 API (LZ4_compress_default / LZ4_decompress_safe).
Path B consumer cases (2026-09-10 真机验证):
  - test_lz4_consumer.c: LZ4F frame API round-trip + dictionary API
    (LZ4_loadDictSlow, v1.10.0 官方转正符号)
  - CLI tool round-trip via the packaged bin/lz4 (R38)
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Lz4TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R34: run the test binary that calls lz4 API
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_lz4")
        self.run(test_bin, env="conanrun")

        # Path B consumer case 1+2: frame API + dictionary API binaries
        consumer_bin = os.path.join(self.cpp.build.bindirs[0], "test_lz4_consumer")
        self.run(consumer_bin, env="conanrun")

        # Path B consumer case: R38 CLI tool shipped in the package must
        # round-trip a file (compress -> decompress -> byte-identical).
        bindir = self.dependencies["lz4"].cpp_info.bindirs[0]
        lz4_cli = os.path.join(bindir, "lz4")
        sample = os.path.join(self.build_folder, "cli_sample.txt")
        packed = sample + ".lz4"
        unpacked = sample + ".out"
        with open(sample, "w") as f:
            f.write("HarmonyOS lz4 CLI consumer round-trip check. " * 16)
        self.run('"%s" -q -f "%s" "%s"' % (lz4_cli, sample, packed), env="conanrun")
        self.run('"%s" -q -d -f "%s" "%s"' % (lz4_cli, packed, unpacked), env="conanrun")
        with open(sample) as f:
            orig = f.read()
        with open(unpacked) as f:
            back = f.read()
        if orig != back:
            raise Exception("lz4 CLI round-trip mismatch")
        print("PASS: consumer case CLI tool round-trip OK")
