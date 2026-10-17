#!/usr/bin/env python3
"""test_package for readstat/1.1.9 — consumer-side verification (L1).

The test() method executes the compiled consumer binary through the Conan run
helper; CI gate L0d/L1a require a real invocation of the artifact, not a stub
whose body only emits a message and returns success.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class ReadstatTestConan(ConanFile):
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
        if not can_run(self):
            self.output.info("cannot run target binaries in this profile; build-only check")
            return
        # cmake_layout puts the executable at the root of the CMake build dir,
        # while `self.cpp.build.bindirs[0]` resolves to "." for a consumer
        # recipe (round-1 evidence: RUN "./test_readstat" → Error 127), so
        # resolve the binary explicitly and run it by absolute path.
        candidates = [
            os.path.join(self.build_folder, "test_readstat"),
            os.path.join(self.cpp.build.bindirs[0], "test_readstat"),
            os.path.join(self.source_folder, "test_readstat"),
        ]
        binary = next((c for c in candidates if os.path.isfile(c)), candidates[0])
        self.output.info(f"consumer check: {binary}")
        self.run(f'"{binary}"', env="conanrun")
