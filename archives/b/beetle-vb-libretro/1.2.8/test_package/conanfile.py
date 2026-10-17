#!/usr/bin/env python3
"""Conan test_package — beetle-vb-libretro 1.2.8 (libretro core).

Consumer-style L1 tests: compile test.c (consumer smoke: public retro_* ABI)
and test_ohos.c (HarmonyOS lifecycle: retro_init → get_system_av_info →
deinit on the OHOS runtime), then dlopen the installed mednafen_vb_libretro.so
and exercise both.
"""
import os

from conan import ConanFile


class BeetlevblibretroTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["beetle-vb-libretro"]
        libdir = dep.cpp_info.libdirs[0]
        core = os.path.join(libdir, "mednafen_vb_libretro.so")
        self.run(
            "clang test.c -o test_beetle-vb-libretro -ldl",
            env="conanbuild",
        )
        self.run(
            "clang test_ohos.c -o test_beetle-vb-libretro-ohos -ldl",
            env="conanbuild",
        )
        # Record the packaged core path for the test() runs
        self._core_path = core

    def test(self):
        core = self._core_path
        self.run(f"./test_beetle-vb-libretro '{core}'", env="conanrun")
        self.run(f"./test_beetle-vb-libretro-ohos '{core}'", env="conanrun")
