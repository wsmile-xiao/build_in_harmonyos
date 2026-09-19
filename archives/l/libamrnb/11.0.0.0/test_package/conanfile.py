#!/usr/bin/env python3
"""Conan test_package for libamrnb — AMR-NB encode/decode round-trip via the
3GPP TS 26.104 interface plus a smoke run of the packaged amrnb-encoder CLI."""
import math
import os
import struct

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibamrnbTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # Also run the test binary directly (CI L0d requires self.run)
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libamrnb")
        self.run(bin_path, env="conanrun")

        # Smoke test the packaged CLI: encode 2 frames (40 ms) of 1 kHz sine
        # and verify the output carries the AMR storage-format magic.
        pcm_path = os.path.join(self.build_folder, "in.pcm")
        amr_path = os.path.join(self.build_folder, "out.amr")
        n_samples = 2 * 160
        with open(pcm_path, "wb") as f:
            for i in range(n_samples):
                s = int(8000.0 * math.sin(2.0 * math.pi * 1000.0 * i / 8000.0))
                f.write(struct.pack("<h", s))
        self.run(f'amrnb-encoder MR122 "{pcm_path}" "{amr_path}"', env="conanrun")
        with open(amr_path, "rb") as f:
            data = f.read()
        if not data.startswith(b"#!AMR\n") or len(data) <= 6 + 12:
            raise AssertionError(
                "amrnb-encoder output is not a valid AMR stream "
                f"(size={len(data)}, head={data[:8]!r})")
        self.output.info(f"amrnb-encoder smoke OK: {len(data)} bytes AMR stream")
