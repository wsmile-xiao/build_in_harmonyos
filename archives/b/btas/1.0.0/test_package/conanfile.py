#!/usr/bin/env python3
"""Conan test_package for btas 1.0.0.

Builds and runs ``test_btas`` against the packaged headers, verifying a
downstream consumer can find_package(btas) and use the tensor algebra API
on the generic backend (version header, feature auto-detection, default
Boost.Container index, scal/axpy/dot/gemm/contract, TensorView round-trip).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class BtasTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()
        # runtime env for shared boost libs linked into the consumer
        # (LD_LIBRARY_PATH etc. captured into conanrunenv-*.sh)
        VirtualRunEnv(self).generate(scope="run")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries directly.
        # Use bash to wrap binary execution where available; run under the
        # Conan run environment so dependency shared libraries resolve.
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} -c './test_btas'",
                 cwd=self.cpp.build.bindirs[0], env="conanrun")
