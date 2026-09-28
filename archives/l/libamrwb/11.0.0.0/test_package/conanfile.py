#!/usr/bin/env python3
"""Conan test_package for libamrwb — AMR-WB encode/decode round-trip via the
3GPP TS 26.204 interface plus a smoke run of the packaged amrwb-encoder CLI."""
import math
import os
import struct

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibamrwbTestConan(ConanFile):
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
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libamrwb")
        self.run(bin_path, env="conanrun")

        # Smoke test the packaged CLI: encode 2 frames (40 ms) of 1 kHz sine
        # at 16 kHz and verify the output carries the AMR-WB storage-format
        # magic "#!AMR-WB\n".
        pcm_path = os.path.join(self.build_folder, "in.pcm")
        amr_path = os.path.join(self.build_folder, "out.amr")
        n_samples = 2 * 320
        with open(pcm_path, "wb") as f:
            for i in range(n_samples):
                s = int(8000.0 * math.sin(2.0 * math.pi * 1000.0 * i / 16000.0))
                f.write(struct.pack("<h", s))
        # mode 8 = 23.85 kbit/s (MR24k); one encoded frame is 61 bytes
        self.run(f'amrwb-encoder 8 "{pcm_path}" "{amr_path}"', env="conanrun")
        with open(amr_path, "rb") as f:
            data = f.read()
        if not data.startswith(b"#!AMR-WB\n") or len(data) < 9 + 2 * 61:
            raise AssertionError(
                "amrwb-encoder output is not a valid AMR-WB stream "
                f"(size={len(data)}, head={data[:12]!r})")
        self.output.info(f"amrwb-encoder smoke OK: {len(data)} bytes AMR-WB stream")
