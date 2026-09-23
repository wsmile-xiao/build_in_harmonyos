#!/usr/bin/env python3
"""Consumer-side test for libkeepalive (Conan L1 test).

libkeepalive is an LD_PRELOAD interposer library: it is not linked into the
consumer, it is loaded by the dynamic loader at run time. The test therefore
builds a plain consumer binary and runs that *same* binary in four
configurations, which is the only way to prove both halves of the contract
("inert unless preloaded" and "active when preloaded"):

  1. no LD_PRELOAD                     -> SO_KEEPALIVE must stay OFF
  2. LD_PRELOAD=libkeepalive.so        -> SO_KEEPALIVE must be ON
  3. + KEEPCNT/KEEPIDLE/KEEPINTVL      -> the requested values must be applied
  4. + KEEPALIVE=off                   -> the injection must be disabled again
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibkeepaliveTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS: /system/bin/sh cannot execute ELF binaries, so drive the
        # consumer through bash (also needed for the inline VAR=value prefixes).
        bash = os.environ.get("CONFIG_SHELL") or next(
            (p for p in ("/data/service/hnp/bin/bash", "/bin/bash", "/usr/bin/bash")
             if os.path.exists(p)), "bash")
        exe = os.path.join(self.cpp.build.bindirs[0], "test_libkeepalive")
        libdir = self.dependencies["libkeepalive"].cpp_info.libdirs[0]
        lib = os.path.join(libdir, "libkeepalive.so")

        self.run(f'{bash} -c "{exe} off"', env="conanrun")
        self.run(f'{bash} -c "LD_PRELOAD={lib} {exe} on"', env="conanrun")
        self.run(f'{bash} -c "KEEPCNT=7 KEEPIDLE=42 KEEPINTVL=13 '
                 f'LD_PRELOAD={lib} {exe} tune"', env="conanrun")
        self.run(f'{bash} -c "KEEPALIVE=off LD_PRELOAD={lib} {exe} off"', env="conanrun")
